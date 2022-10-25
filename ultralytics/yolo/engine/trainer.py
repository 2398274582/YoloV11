"""
Simple training loop; Boilerplate that could apply to any arbitrary neural network,
"""

import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Union

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn as nn
from omegaconf import DictConfig, OmegaConf
from torch.cuda import amp
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

import ultralytics.yolo.utils as utils
import ultralytics.yolo.utils.loggers as loggers
from ultralytics.yolo.utils import LOGGER, ROOT
from ultralytics.yolo.utils.files import increment_path, save_yaml

CONFIG_PATH_ABS = ROOT / "yolo/utils/configs"
DEFAULT_CONFIG = "defaults.yaml"


class BaseTrainer:

    def __init__(self, config=CONFIG_PATH_ABS / DEFAULT_CONFIG, overrides={}):
        self.console = LOGGER
        self.args = self._get_config(config, overrides)
        self.validator = None
        self.callbacks = defaultdict(list)
        self.console.info(f"Training config: \n args: \n {self.args}")  # to debug
        # Directories
        self.save_dir = increment_path(Path(self.args.project) / self.args.name, exist_ok=self.args.exist_ok)
        self.wdir = self.save_dir / 'weights'
        self.wdir.mkdir(parents=True, exist_ok=True)  # make dir
        self.last, self.best = self.wdir / 'last.pt', self.wdir / 'best.pt'

        # Save run settings
        save_yaml(self.save_dir / 'args.yaml', OmegaConf.to_container(self.args, resolve=True))

        # device
        self.device = utils.torch_utils.select_device(self.args.device, self.args.batch_size)
        self.console.info(f"running on device {self.device}")
        self.scaler = amp.GradScaler(enabled=self.device.type != 'cpu')

        # Model and Dataloaders.
        self.trainset, self.testset = self.get_dataset(self.args.data)
        self.model = self.get_model(self.args.model, self.args.pretrained).to(self.device)

        # epoch level metrics
        self.metrics = {}  # handle metrics returned by validator
        self.best_fitness = None
        self.fitness = None
        self.loss = None

        for callback, func in loggers.default_callbacks.items():
            self.add_callback(callback, func)

    def _get_config(self, config: Union[str, DictConfig], overrides: Union[str, Dict] = {}):
        """
        Accepts yaml file name or DictConfig containing experiment configuration.
        Returns training args namespace
        :param config: Optional file name or DictConfig object
        """
        if isinstance(config, (str, Path)):
            config = OmegaConf.load(config)
        elif isinstance(config, Dict):
            config = OmegaConf.create(config)

        # override
        if isinstance(overrides, str):
            overrides = OmegaConf.load(overrides)
        elif isinstance(overrides, Dict):
            overrides = OmegaConf.create(overrides)

        config = OmegaConf.merge(config, overrides)
        return config

    def add_callback(self, onevent: str, callback):
        """
        appends the given callback
        """
        self.callbacks[onevent].append(callback)

    def set_callback(self, onevent: str, callback):
        """
        overrides the existing callbacks with the given callback
        """
        self.callbacks[onevent] = [callback]

    def trigger_callbacks(self, onevent: str):
        for callback in self.callbacks.get(onevent, []):
            callback(self)

    def train(self):
        world_size = torch.cuda.device_count()
        if world_size > 1:
            mp.spawn(self._do_train, args=(world_size,), nprocs=world_size, join=True)
        else:
            self._do_train(-1, 1)

    def _setup_ddp(self, rank, world_size):
        os.environ['MASTER_ADDR'] = 'localhost'
        os.environ['MASTER_PORT'] = '9020'
        torch.cuda.set_device(rank)
        self.device = torch.device('cuda', rank)
        print(f"RANK - WORLD_SIZE - DEVICE: {rank} - {world_size} - {self.device} ")

        dist.init_process_group("nccl" if dist.is_nccl_available() else "gloo", rank=rank, world_size=world_size)
        self.model = self.model.to(self.device)
        self.model = DDP(self.model, device_ids=[rank])
        self.args.batch_size = self.args.batch_size // world_size

    def _setup_train(self, rank):
        """
        Builds dataloaders and optimizer on correct rank process
        """
        self.optimizer = build_optimizer(model=self.model,
                                         name=self.args.optimizer,
                                         lr=self.args.lr0,
                                         momentum=self.args.momentum,
                                         decay=self.args.weight_decay)
        self.train_loader = self.get_dataloader(self.trainset, batch_size=self.args.batch_size, rank=rank)
        if rank in {0, -1}:
            print(" Creating testloader rank :", rank)
            self.test_loader = self.get_dataloader(self.testset, batch_size=self.args.batch_size * 2, rank=rank)
            self.validator = self.get_validator()
            print("created testloader :", rank)

    def _do_train(self, rank, world_size):
        if world_size > 1:
            self._setup_ddp(rank, world_size)

        # callback hook. before_train
        self._setup_train(rank)

        self.epoch = 1
        self.epoch_time = None
        self.epoch_time_start = time.time()
        self.train_time_start = time.time()
        for epoch in range(self.args.epochs):
            # callback hook. on_epoch_start
            self.model.train()
            pbar = enumerate(self.train_loader)
            if rank in {-1, 0}:
                pbar = tqdm(enumerate(self.train_loader),
                            total=len(self.train_loader),
                            bar_format='{l_bar}{bar:10}{r_bar}{bar:-10b}')
            tloss = 0
            for i, (images, labels) in pbar:
                # callback hook. on_batch_start
                # forward
                images, labels = self.preprocess_batch(images, labels)
                self.loss = self.criterion(self.model(images), labels)
                tloss = (tloss * i + self.loss.item()) / (i + 1)

                # backward
                self.model.zero_grad(set_to_none=True)
                self.scaler.scale(self.loss).backward()

                # optimize
                self.optimizer_step()
                self.trigger_callbacks('on_batch_end')

                # log
                mem = '%.3gG' % (torch.cuda.memory_reserved() / 1E9 if torch.cuda.is_available() else 0)  # (GB)
                if rank in {-1, 0}:
                    pbar.desc = f"{f'{epoch + 1}/{self.args.epochs}':>10}{mem:>10}{tloss:>12.3g}" + ' ' * 36

            if rank in [-1, 0]:
                # validation
                # callback: on_val_start()
                self.validate()
                # callback: on_val_end()

                # save model
                if (not self.args.nosave) or (self.epoch + 1 == self.args.epochs):
                    self.save_model()
                    # callback; on_model_save

            self.epoch += 1
            tnow = time.time()
            self.epoch_time = tnow - self.epoch_time_start
            self.epoch_time_start = tnow

            # TODO: termination condition

        self.log(f"\nTraining complete ({(time.time() - self.train_time_start) / 3600:.3f} hours) \
                            \n{self.usage_help()}")
        # callback; on_train_end
        dist.destroy_process_group() if world_size != 1 else None

    def save_model(self):
        ckpt = {
            'epoch': self.epoch,
            'best_fitness': self.best_fitness,
            'model': None,  # deepcopy(ema.ema).half(),  # deepcopy(de_parallel(model)).half(),
            'ema': None,  # deepcopy(ema.ema).half(),
            'updates': None,  # ema.updates,
            'optimizer': None,  # optimizer.state_dict(),
            'train_args': self.args,
            'date': datetime.now().isoformat()}

        # Save last, best and delete
        torch.save(ckpt, self.last)
        if self.best_fitness == self.fitness:
            torch.save(ckpt, self.best)
        del ckpt

    def get_dataloader(self, dataset_path, batch_size=16, rank=0):
        """
        Returns dataloader derived from torch.data.Dataloader
        """
        pass

    def get_dataset(self, data):
        """
        Download the dataset if needed and verify it.
        Returns train and val split datasets
        """
        pass

    def get_model(self, model, pretrained=True):
        """
        load/create/download model for any task
        """
        pass

    def get_validator(self):
        pass

    def optimizer_step(self):
        self.scaler.unscale_(self.optimizer)  # unscale gradients
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)  # clip gradients
        self.scaler.step(self.optimizer)
        self.scaler.update()
        self.optimizer.zero_grad()

    def preprocess_batch(self, images, labels):
        """
        Allows custom preprocessing model inputs and ground truths depending on task type
        """
        return images.to(self.device, non_blocking=True), labels.to(self.device)

    def validate(self):
        """
        Runs validation on test set using self.validator.
        # TODO: discuss validator class. Enforce that a validator metrics dict should contain
        "fitness" metric.
        """
        self.metrics = self.validator(self)
        self.fitness = self.metrics.get("fitness") or (-self.loss)  # use loss as fitness measure if not found
        if not self.best_fitness or self.best_fitness < self.fitness:
            self.best_fitness = self.fitness

    def build_targets(self, preds, targets):
        pass

    def criterion(self, preds, targets):
        pass

    def progress_string(self):
        """
        Returns progress string depending on task type.
        """
        pass

    def usage_help(self):
        """
        Returns usage functionality. gets printed to the console after training.
        """
        pass

    def log(self, text, rank=-1):
        """
        Logs the given text to given ranks process if provided, otherwise logs to all ranks
        :param text: text to log
        :param rank: List[Int]

        """
        if rank in {-1, 0}:
            self.console.info(text)


def build_optimizer(model, name='Adam', lr=0.001, momentum=0.9, decay=1e-5):
    # TODO: 1. docstring with example? 2. Move this inside Trainer? or utils?
    # YOLOv5 3-param group optimizer: 0) weights with decay, 1) weights no decay, 2) biases no decay
    g = [], [], []  # optimizer parameter groups
    bn = tuple(v for k, v in nn.__dict__.items() if 'Norm' in k)  # normalization layers, i.e. BatchNorm2d()
    for v in model.modules():
        if hasattr(v, 'bias') and isinstance(v.bias, nn.Parameter):  # bias (no decay)
            g[2].append(v.bias)
        if isinstance(v, bn):  # weight (no decay)
            g[1].append(v.weight)
        elif hasattr(v, 'weight') and isinstance(v.weight, nn.Parameter):  # weight (with decay)
            g[0].append(v.weight)

    if name == 'Adam':
        optimizer = torch.optim.Adam(g[2], lr=lr, betas=(momentum, 0.999))  # adjust beta1 to momentum
    elif name == 'AdamW':
        optimizer = torch.optim.AdamW(g[2], lr=lr, betas=(momentum, 0.999), weight_decay=0.0)
    elif name == 'RMSProp':
        optimizer = torch.optim.RMSprop(g[2], lr=lr, momentum=momentum)
    elif name == 'SGD':
        optimizer = torch.optim.SGD(g[2], lr=lr, momentum=momentum, nesterov=True)
    else:
        raise NotImplementedError(f'Optimizer {name} not implemented.')

    optimizer.add_param_group({'params': g[0], 'weight_decay': decay})  # add g0 with weight_decay
    optimizer.add_param_group({'params': g[1], 'weight_decay': 0.0})  # add g1 (BatchNorm2d weights)
    LOGGER.info(f"optimizer: {type(optimizer).__name__}(lr={lr}) with parameter groups "
                f"{len(g[1])} weight(decay=0.0), {len(g[0])} weight(decay={decay}), {len(g[2])} bias")
    return optimizer


# Dummy validator
def val(trainer: BaseTrainer):
    trainer.console.info("validating")
    return {"metric_1": 0.1, "metric_2": 0.2, "fitness": 1}
