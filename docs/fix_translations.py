"""
Script to fix broken Markdown links and front matter in language-specific directories.

This script processes markdown files in language-specific directories (like /zh/).
It finds Markdown links and checks their existence. If a link is broken and does not exist
in the language-specific directory but exists in the /en/ directory, the script updates
the link to point to the corresponding file in the /en/ directory.

It also ensures that front matter keywords like 'comments:', 'description:', and 'keywords:'
are not translated and remain in English.
"""

import re
from pathlib import Path


class MarkdownLinkFixer:
    """Class to fix Markdown links and front matter in language-specific directories."""

    def __init__(self, base_dir, update_links=False, update_frontmatter=False):
        """Initialize the MarkdownLinkFixer with the base directory."""
        self.base_dir = Path(base_dir)
        self.update_links = update_links
        self.update_frontmatter = update_frontmatter
        self.md_link_regex = re.compile(r'\[([^\]]+)\]\(([^:\)]+)\.md\)')
        self.front_matter_regex = re.compile(r'^(comments|description|keywords):.*$', re.MULTILINE)
        self.translations = {
            'zh': ['评论', '描述', '关键词'],  # Mandarin Chinese (Simplified)
            'es': ['comentarios', 'descripción', 'palabras clave'],  # Spanish
            'ru': ['комментарии', 'описание', 'ключевые слова'],  # Russian
            'pt': ['comentários', 'descrição', 'palavras-chave'],  # Portuguese
            'fr': ['commentaires', 'description', 'mots-clés'],  # French
            'de': ['Kommentare', 'Beschreibung', 'Schlüsselwörter'],  # German
            'ja': ['コメント', '説明', 'キーワード'],  # Japanese
            'ko': ['댓글', '설명', '키워드']  # Korean
        }  # front matter translations for comments, description, keyword

    def replace_front_matter(self, content):
        """Ensure front matter keywords remain in English."""
        english_keys = ['comments', 'description', 'keywords']

        for lang, terms in self.translations.items():
            for term, eng_key in zip(terms, english_keys):
                if eng_key == 'comments':
                    # Replace comments key and set its value to 'true'
                    content = re.sub(rf'{term} *:.*', f'{eng_key}: true', content)
                else:
                    content = re.sub(rf'{term} *:', f'{eng_key}:', content)

        return content

    def link_replacer(self, match, parent_dir, lang_dir):
        """Replace broken links with corresponding links in the /en/ directory."""
        text, path = match.groups()
        linked_path = (parent_dir / path).resolve().with_suffix('.md')

        if not linked_path.exists():
            en_linked_path = Path(str(linked_path).replace(str(lang_dir), str(lang_dir.parent / 'en')))
            if en_linked_path.exists():
                steps_up = len(parent_dir.relative_to(self.base_dir).parts)
                relative_path = Path('../' * steps_up) / en_linked_path.relative_to(self.base_dir)
                relative_path = str(relative_path).replace('/en/', '/')
                print(f"Redirecting link '[{text}]({path})' from {parent_dir} to {relative_path}")
                return f'[{text}]({relative_path})'
            else:
                print(f"Warning: Broken link '[{text}]({path})' found in {parent_dir} does not exist in /docs/en/.")
        return match.group(0)

    def process_markdown_file(self, md_file_path, lang_dir):
        """Process each markdown file in the language directory."""
        print(f"Processing file: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        if self.update_links:
            content = self.md_link_regex.sub(lambda m: self.link_replacer(m, md_file_path.parent, lang_dir), content)

        if self.update_frontmatter:
            content = self.replace_front_matter(content)

        with open(md_file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def process_language_directory(self, lang_dir):
        """Process each language-specific directory."""
        print(f"Processing language directory: {lang_dir}")
        for md_file in lang_dir.rglob('*.md'):
            self.process_markdown_file(md_file, lang_dir)

    def run(self):
        """Run the link fixing and front matter updating process for each language-specific directory."""
        for subdir in self.base_dir.iterdir():
            if subdir.is_dir() and re.match(r'^\w\w$', subdir.name) and subdir.name != 'en':
                self.process_language_directory(subdir)


if __name__ == '__main__':
    # Set the path to your MkDocs 'docs' directory here
    docs_dir = str(Path(__file__).parent.resolve())
    fixer = MarkdownLinkFixer(docs_dir, update_links=False, update_frontmatter=True)
    fixer.run()
