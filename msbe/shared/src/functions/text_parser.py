"""
Text Parser function for converting markdown/HTML to plain text.

This function detects and converts formatted text to human-readable plain text.
"""

import re
from html.parser import HTMLParser


class TextParser:
    """
    Parser for converting markdown and HTML to plain text.
    """
    
    @staticmethod
    def parse_markdown(text: str) -> str:
        """
        Convert markdown to plain text.
        
        Args:
            text: Markdown text
            
        Returns:
            Plain text with markdown formatting removed
        """
        try:
            # Remove code blocks
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'`[^`]+`', '', text)
            
            # Remove headers (keep text)
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            
            # Remove bold/italic
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            text = re.sub(r'__([^_]+)__', r'\1', text)
            text = re.sub(r'_([^_]+)_', r'\1', text)
            
            # Remove links (keep text)
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            
            # Remove images
            text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
            
            # Remove horizontal rules
            text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
            
            # Clean up extra whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text.strip()
            
        except Exception:
            return text
    
    @staticmethod
    def parse_html(text: str) -> str:
        """
        Convert HTML to plain text.
        
        Args:
            text: HTML text
            
        Returns:
            Plain text with HTML tags removed
        """
        try:
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                
                def handle_data(self, data):
                    self.text_parts.append(data)
                
                def get_text(self):
                    return ''.join(self.text_parts)
            
            parser = HTMLTextExtractor()
            parser.feed(text)
            plain_text = parser.get_text()
            
            # Clean up extra whitespace
            plain_text = re.sub(r'\n{3,}', '\n\n', plain_text)
            plain_text = re.sub(r' {2,}', ' ', plain_text)
            
            return plain_text.strip()
            
        except Exception:
            return text
    
    @staticmethod
    def auto_parse(text: str) -> str:
        """
        Automatically detect and parse markdown or HTML.
        
        Args:
            text: Text that may contain markdown or HTML
            
        Returns:
            Parsed plain text
        """
        # Check for HTML
        if '<html' in text.lower() or '<body' in text.lower() or '<div' in text.lower():
            return TextParser.parse_html(text)
        
        # Check for markdown
        markdown_patterns = [
            r'^#{1,6}\s+',
            r'\*\*[^*]+\*\*',
            r'\[[^\]]+\]\([^\)]+\)',
            r'```',
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return TextParser.parse_markdown(text)
        
        # No formatting detected
        return text
