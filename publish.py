#!/usr/bin/env python3
# md2html.py

import re
import sys
from pathlib import Path
from datetime import datetime

def convert_md_to_html(md_content):
    """Конвертирует Markdown в HTML с поддержкой Obsidian синтаксиса"""
    
    html = md_content
    
    # Таблицы (обрабатываем до других преобразований)
    html = convert_tables(html)
    
    # Заголовки (# ## ### и т.д.)
    html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Изображения Obsidian: ![[image.png]] -> <img src="image.png">
    html = re.sub(r'!\[\[(.+?)\]\]', r'<img src="../md/images/\1" alt="\1">', html)
    
    # Обычные изображения Markdown: ![alt](url)
    html = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'<img src="\2" alt="\1">', html)
    
    # Ссылки: [text](url)
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Выделение текста (highlight) Obsidian: ==text==
    html = re.sub(r'==(.+?)==', r'<mark>\1</mark>', html)
    
    # Жирный текст: **text** или __text__
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
    
    # Курсив: *text* или _text_
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\b_(.+?)_\b', r'<em>\1</em>', html)
    
    # Зачеркнутый: ~~text~~
    html = re.sub(r'~~(.+?)~~', r'<del>\1</del>', html)
    
    # Блоки кода: ```lang\ncode\n``` (обрабатываем до inline кода)
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code class="language-\1">\2</code></pre>', html, flags=re.DOTALL)
    
    # Код inline: `code`
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Горизонтальная линия: --- или ***
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    html = re.sub(r'^\*\*\*$', r'<hr>', html, flags=re.MULTILINE)
    
    # Вложенные списки (новая логика)
    html = convert_nested_lists(html)
    
    # Цитаты: > text
    html = re.sub(r'^>\s+(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # НОВАЯ ЛОГИКА: одна пустая строка = <br>
    # Заменяем одиночные пустые строки на маркер
    html = re.sub(r'\n\n', r'\n{{SINGLE_BR}}\n', html)
    
    # Параграфы
    lines = html.split('\n')
    result = []
    in_p = False
    paragraph_content = []
    
    for line in lines:
        stripped = line.strip()
        
        # Маркер для <br>
        if stripped == '{{SINGLE_BR}}':
            if in_p:
                result.append('<p>' + ' '.join(paragraph_content) + '</p>')
                paragraph_content = []
                in_p = False
            result.append('<br>')
            continue
        
        # Это HTML тег или пустая строка
        if not stripped or stripped.startswith('<'):
            # Закрываем параграф если он был открыт
            if in_p:
                result.append('<p>' + ' '.join(paragraph_content) + '</p>')
                paragraph_content = []
                in_p = False
            
            # Добавляем HTML тег или пустую строку
            if stripped:
                result.append(line)
        else:
            # Это обычный текст - добавляем в параграф
            if not in_p:
                in_p = True
            paragraph_content.append(stripped)
    
    # Закрываем последний параграф если остался
    if in_p:
        result.append('<p>' + ' '.join(paragraph_content) + '</p>')
    
    html = '\n'.join(result)
    
    return html

def get_indent_level(line):
    """Определяет уровень вложенности по табам/пробелам"""
    indent = 0
    for char in line:
        if char == '\t':
            indent += 1
        elif char == ' ':
            # Считаем 4 пробела = 1 таб
            indent += 0.25
        else:
            break
    return int(indent)

def convert_nested_lists(text):
    """Конвертирует вложенные списки в HTML"""
    lines = text.split('\n')
    result = []
    
    # Стек для отслеживания открытых списков
    # Каждый элемент: (тип, уровень) где тип = 'ul' или 'ol'
    list_stack = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Проверяем неупорядоченный список
        ul_match = re.match(r'^(\t*|\s*)[\*\-]\s+(.+)$', line)
        # Проверяем упорядоченный список
        ol_match = re.match(r'^(\t*|\s*)\d+\.\s+(.+)$', line)
        
        if ul_match or ol_match:
            if ul_match:
                indent_str, content = ul_match.groups()
                list_type = 'ul'
            else:
                indent_str, content = ol_match.groups()
                list_type = 'ol'
            
            current_level = get_indent_level(indent_str)
            
            # Закрываем списки глубже текущего уровня
            while list_stack and list_stack[-1][1] > current_level:
                closed_type, _ = list_stack.pop()
                result.append(f'</{closed_type}>')
                if list_stack:
                    result.append('</li>')
            
            # Если уровень совпадает, но тип другой - закрываем и открываем новый
            if list_stack and list_stack[-1][1] == current_level and list_stack[-1][0] != list_type:
                result.append('</li>')
                closed_type, _ = list_stack.pop()
                result.append(f'</{closed_type}>')
                
            # Если стек пуст или нужен новый уровень
            if not list_stack or list_stack[-1][1] < current_level:
                result.append(f'<{list_type}>')
                list_stack.append((list_type, current_level))
            elif list_stack and list_stack[-1][1] == current_level:
                # Закрываем предыдущий элемент списка
                result.append('</li>')
            
            result.append(f'<li>{content}')
            
        else:
            # Не список - закрываем все открытые списки
            if list_stack:
                result.append('</li>')
                while list_stack:
                    list_type, _ = list_stack.pop()
                    result.append(f'</{list_type}>')
            
            result.append(line)
        
        i += 1
    
    # Закрываем оставшиеся открытые списки
    if list_stack:
        result.append('</li>')
        while list_stack:
            list_type, _ = list_stack.pop()
            result.append(f'</{list_type}>')
    
    return '\n'.join(result)

def convert_tables(text):
    """Конвертирует Markdown таблицы в HTML"""
    lines = text.split('\n')
    result = []
    in_table = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Проверяем, начинается ли таблица (строка с | и следующая строка с |---|)
        if '|' in line and i + 1 < len(lines) and re.match(r'^\s*\|?[\s\-:|]+\|[\s\-:|]*$', lines[i + 1]):
            if not in_table:
                result.append('<table>')
                in_table = True
            
            # Заголовок таблицы
            headers = [cell.strip() for cell in line.split('|')]
            headers = [h for h in headers if h]  # Убираем пустые элементы
            
            result.append('<thead>')
            result.append('<tr>')
            for header in headers:
                result.append(f'<th>{header}</th>')
            result.append('</tr>')
            result.append('</thead>')
            result.append('<tbody>')
            
            i += 2  # Пропускаем разделитель
            
            # Строки таблицы
            while i < len(lines) and '|' in lines[i]:
                row_line = lines[i]
                cells = [cell.strip() for cell in row_line.split('|')]
                cells = [c for c in cells if c]  # Убираем пустые элементы
                
                result.append('<tr>')
                for cell in cells:
                    result.append(f'<td>{cell}</td>')
                result.append('</tr>')
                i += 1
            
            result.append('</tbody>')
            result.append('</table>')
            in_table = False
            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

def extract_first_heading(md_content):
    """Извлекает первый заголовок из Markdown контента"""
    # Ищем первый заголовок любого уровня
    match = re.search(r'^#{1,6}\s+(.+)$', md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Без заголовка"

def update_blog_list(output_file, title):
    """Обновляет список статей в blog.html"""
    blog_path = Path('articles/blog.html')
    
    # Создаем директорию и файл, если их нет
    if not blog_path.parent.exists():
        blog_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not blog_path.exists():
        # Создаем новый blog.html
        blog_content = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<title>Блог</title>
<link href="styles.css" rel="stylesheet"/>
</head>
<body>
<h1>Все статьи</h1>
<div id="articles-list">
<!-- ARTICLES -->
</div>
</body>
</html>"""
        with open(blog_path, 'w', encoding='utf-8') as f:
            f.write(blog_content)
    
    # Читаем blog.html
    with open(blog_path, 'r', encoding='utf-8') as f:
        blog_content = f.read()
    
    # Получаем имя файла относительно articles/
    article_filename = output_file.name
    
    # Проверяем, есть ли уже ссылка на эту статью
    if f'href="{article_filename}"' in blog_content:
        print(f"  → Статья уже есть в blog.html, обновляем заголовок")
        # Обновляем заголовок существующей статьи
        pattern = f'<a class="article-card" href="{article_filename}"><h2>.*?</h2></a>'
        replacement = f'<a class="article-card" href="{article_filename}"><h2>{title}</h2></a>'
        blog_content = re.sub(pattern, replacement, blog_content)
    else:
        print(f"  → Добавляем новую статью в blog.html")
        # Добавляем новую ссылку после комментария <!-- ARTICLES -->
        new_article = f'<a class="article-card" href="{article_filename}"><h2>{title}</h2></a>'
        blog_content = blog_content.replace(
            '<!-- ARTICLES -->',
            f'<!-- ARTICLES -->\n{new_article}'
        )
    
    # Сохраняем обновленный blog.html
    with open(blog_path, 'w', encoding='utf-8') as f:
        f.write(blog_content)

def create_html_document(body_content, title="Converted Document"):
    """Создает полный HTML документ"""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
{body_content}
</body>
</html>"""

def transliterate_filename(filename):
    """Транслитерация имени файла в латиницу"""
    translit_map = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
        'ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m',
        'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
        'ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
        'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
    }

    result = []
    for char in filename.lower():
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isalnum() or char in ('-', '_'):
            result.append(char)
        elif char in (' ', '.'):
            result.append('-')
        # остальные символы пропускаем

    return ''.join(result)

def main():
    if len(sys.argv) < 2:
        print("Использование: python md2html.py input.md [output.html]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"Ошибка: файл {input_file} не найден")
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])
    else:
        # Создаем папку articles если её нет
        articles_dir = Path("articles")
        articles_dir.mkdir(parents=True, exist_ok=True)

        # Берем имя исходного файла, переводим в латиницу
        transliterated_name = transliterate_filename(input_file.stem)

        # Сохраняем в articles/
        output_file = articles_dir / f"{transliterated_name}.html"
    
    # Читаем Markdown файл
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Извлекаем первый заголовок
    article_title = extract_first_heading(md_content)
    
    # Конвертируем в HTML
    html_body = convert_md_to_html(md_content)
    
    # Создаем полный HTML документ
    title = article_title  # Используем извлеченный заголовок
    full_html = create_html_document(html_body, title)
    
    # Сохраняем результат
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ Конвертация завершена: {output_file}")
    print(f"  Заголовок статьи: {article_title}")
    
    # Обновляем blog.html
    update_blog_list(output_file, article_title)
    print(f"✓ blog.html обновлен")

if __name__ == "__main__":
    main()