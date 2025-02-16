#!/usr/bin/env python3
import sys
import re
import random
from termcolor import colored
import os
import time
from importlib import resources
import termios
import tty
import yaml

def load_config(config_file):
    if not config_file:
        raise ValueError("Config file path is empty.")
    try:
        with open(config_file, 'r') as f:
            try:
                config = yaml.safe_load(f)
                return config or {}
            except yaml.YAMLError as e:
                print(colored(f"Warning: Invalid YAML syntax in {config_file}: {e}", "red"))
                print("Loading default settings.")
                return {}
    except FileNotFoundError:
        print("Config file not found. Creating with default settings.")  # Log file not found
        # Create the config file with default settings
        default_settings = {
            'colors': {
                'headword': 'light_green',
                'grammar': 'yellow',
                'match': 'grey',
                'highlight_background': 'yellow'
            },
            'flashcard_count': 10,
            'silent_fail': False,
            'random_word_count': 1,
            'random_headword_count': 1,
            'quiz_word_count': 10,
            'fallback_to_prefix': True
        }
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.safe_dump(default_settings, f)
        return default_settings
    
def get_settings():
    config_dir = os.path.expanduser("~/.config/nordic/")
    os.makedirs(config_dir, exist_ok=True)  # Ensure the directory exists
    config_file = os.path.join(config_dir, "config.yaml")
    settings = load_config(config_file)
    # Ensure default colors and other settings exist if not found in the loaded config
    default_colors = {
        'headword': 'light_green',
        'grammar': 'yellow',
        'match': 'grey',
        'highlight_background': 'yellow'
    }
    settings['colors'] = {**default_colors, **settings.get('colors', {})}
    return settings


def print_help():
    print("Norwegian-English Dictionary Search Tool")
    print("\nUsage:")
    print("  nordic <search_term>")
    print("\nSearch patterns:")
    print("  - Exact match in main term: ære (matches ære¹, ære², etc.). If no exact matches, defaults to prefix match.")
    print("  - Prefix match in main term, add @ after search term: ære@ (matches 'ære', 'æresdrap', etc.)")
    print("  - Match anywhere in term, add @ before the search: @ære or @ære@ (matches 'ære', 'æresdrap', 'lærebok', etc.)")
    print("  - Full text search in term or all content, add % before search term: %nasjonal (searches terms and definitions)")
    
    print("  nordic -l|--list <category>")
    print("\nList categories:")
    print("  m   - masculine nouns")
    print("  f   - feminine nouns")
    print("  c   - common gender nouns (m/f)")
    print("  n   - neuter nouns")
    print("  w   - nouns without gender")
    print("  adj - adjectives")
    print("  v   - verbs")
    print("  adv - adverbs")
    print("  u   - unidentified type words")
    print("\nOther commands:")
    print("  -s|--stats  Provides a series of statistics about the dictionary.")
    print("  -e|--english <word>    Search for English word in definitions")
    print("  -r[N]  Get N random words with their definitions (default: 1)")
    print("  -R[N]  Get N random words (default: 1)")
    print("  -f[N]  Flashcard mode with N random words (usually default: 10)")
    print("  -q[N]  Quiz mode with N random words (usually default: 10)")
    print("  -t|--test  Run some test searches. If you add a word, it will run exact search on that word but return raw markdown")
    print("  -x|--examples <term> Search for exact match definition plus sample sentences containing the term in the Tatoeba database.")
    
    print("\nConfiguration Options in ~/.config/nordic/nordic.yaml:")
    print("  colors:")
    print("    headword           Color for headword highlighting.")
    print("    match              Color for matched text in wildcard searches.")
    print("    highlight_background Color for the background of highlighted matches.")
    print("  quiz_word_count      Default number of words for quiz mode.")
    print("  flashcard_count      Default number of words for flashcard mode.")
    print("  random_word_count    Default number of words for random word retrieval.")
    print("  random_headword_count Default number of random headwords.")
    print("  fallback_to_prefix   Will fall back to prefix search if no exact match is found when set to True.")
    print("  silent_fail          Suppress 'no entry found' messages when set to True.")

def normalize_headword(head_term):
    """Remove trailing superscript numbers (¹, ², ³) from the headword."""
    return re.sub(r'[¹²³⁴]', '', head_term)

def word_matches(head_term, search_term):
    """Match the headword based on search_term patterns."""
    normalized_head = normalize_headword(head_term)
    if search_term.startswith('@') and search_term.endswith('@'):
        return search_term[1:-1].lower() in normalized_head.lower()
    elif search_term.startswith('@'):
        return search_term[1:].lower() in normalized_head.lower()
    elif search_term.endswith('@'):
        return normalized_head.lower().startswith(search_term[:-1].lower())
    else:
        # First try exact match
        if normalized_head.lower() == search_term.lower():
            return True
        # If no exact match, try prefix match (using startswith instead of in)
        return normalized_head.lower().startswith(search_term.lower())

def highlight_match(word, search_term, settings, tatoeba=False):
    """Highlight the matching portion of a word for wildcard searches while preserving original color."""
    if not search_term.startswith('@'):
        return colored(word, settings['colors']['headword'])
        
    # Remove @ symbols and convert to lowercase for matching
    clean_search = search_term.strip('@').lower()
    word_lower = word.lower()
    
    # Find the match position
    match_start = word_lower.find(clean_search)
    if match_start == -1:  # No match found
        return colored(word, settings['colors']['headword'])
        
    match_end = match_start + len(clean_search)
    
    # Split the word into parts
    pre_match = word[:match_start]
    matched = word[match_start:match_end]
    post_match = word[match_end:]
    
    # Return the word with highlights but preserving original text color
    if tatoeba:
        return (pre_match + 
            colored(matched, settings['colors']['match'], 'on_' + settings['colors']['highlight_background']) + 
            post_match)
    else:
        return (colored(pre_match, settings['colors']['headword']) + 
                colored(matched, settings['colors']['match'], 'on_' + settings['colors']['highlight_background']) + 
                colored(post_match, settings['colors']['headword']))


def get_char():
    """Get a single character from the user without requiring Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def highlight_text(text, search_term, settings):
    """Highlight all occurrences of search term in text while preserving existing formatting."""
    if not text:
        return text
        
    # First process any markdown formatting to preserve colors
    bold_parts = re.findall(r'\*\*(.*?)\*\*', text)
    for bold in bold_parts:
        text = text.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
    
    italic_parts = re.findall(r'\*(.*?)\*', text)
    for italic in italic_parts:
        text = text.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
    
    # Now highlight the search term
    parts = []
    last_end = 0
    text_lower = text.lower()
    search_lower = search_term.lower()
    
    while True:
        start = text_lower.find(search_lower, last_end)
        if start == -1:
            parts.append(text[last_end:])
            break
            
        parts.append(text[last_end:start])
        matched = text[start:start + len(search_term)]
        parts.append(colored(matched, settings['colors']['match'], 'on_' + settings['colors']['highlight_background']))
        
        last_end = start + len(search_term)
    
    return ''.join(parts)

# ----------------------------------------

def search_dictionary(content, search_term, settings):
    main_entry_pattern = r'^\s*[-•]\s+\*?\*?([^\s*]+)(?:\*\*)?(.*?)$'
    
    # Handle full-text search with %
    if search_term.startswith('%'):
        return fulltext_search(content, search_term[1:],settings)  # Remove % and use dedicated function
    
    # Original search logic for @, exact, and prefix matches
    exact_matches = []
    partial_matches = []
    is_wildcard = '@' in search_term
    
    lines = content.split('\n')
    
    # First pass: collect all potential matches
    for i, line in enumerate(lines):
        match = re.match(main_entry_pattern, line)
        if match and match.group(1):
            head_term = match.group(1).strip('*')
            
            # For wildcard searches, use word_matches
            if is_wildcard:
                if word_matches(head_term, search_term):
                    partial_matches.append((i, line))
            else:
                # For non-wildcard, try exact match first
                if normalize_headword(head_term).lower() == search_term.lower():
                    exact_matches.append((i, line))
                # Then try prefix match
                elif normalize_headword(head_term).lower().startswith(search_term.lower()):
                    partial_matches.append((i, line))
    
    # Handle matches display
    if is_wildcard:
        matches_to_print = partial_matches
    elif exact_matches:
        matches_to_print = exact_matches
    else:
        if partial_matches and settings.get('fallback_to_prefix', False):
            print("No exact matches. Partial matches:\n")
            time.sleep(0.5)
            matches_to_print = partial_matches
        else:
            matches_to_print = []
            if not settings.get('silent_fail', False):
                print(f"No entries found for '{search_term}'")
            return
        
    
    # Show headers only for wildcard searches that match across the dictionary
    show_headers = search_term.startswith('@')

    current_letter = ''
    is_first_entry = True
    for i, line in matches_to_print:
        match = re.match(main_entry_pattern, line)
        if match and match.group(1):
            head_term = match.group(1).strip('*')

            if show_headers:
                first_letter = head_term[0].upper()
                if first_letter != current_letter:
                    current_letter = first_letter
                    print(f"\n --- {current_letter} ---\n", end='')
                    is_first_entry = True

            rest_of_line = match.group(2)
            
            # Apply colors and highlighting
            if is_wildcard and search_term.startswith('@'):
                head_term = highlight_match(head_term, search_term, settings)
            else:
                head_term = colored(head_term, settings['colors']['headword'])
                
            bold_parts = re.findall(r'\*\*(.*?)\*\*', rest_of_line)
            for bold in bold_parts:
                rest_of_line = rest_of_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
            italic_parts = re.findall(r'\*(.*?)\*', rest_of_line)
            for italic in italic_parts:
                rest_of_line = rest_of_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
            
            if not is_first_entry:
                print()
            else:
                is_first_entry = False
            
            print(f"- {head_term}{rest_of_line}", end='')

            # Process subentries
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r'^[-•]\s+', next_line) and not re.match(r'^\s{3}[-•]\s+', next_line):
                    break
                if next_line.strip() == '':
                    break
                if next_line.strip():
                    # Format subentry
                    bold_parts = re.findall(r'\*\*(.*?)\*\*', next_line)
                    for bold in bold_parts:
                        next_line = next_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                    italic_parts = re.findall(r'\*(.*?)\*', next_line)
                    for italic in italic_parts:
                        next_line = next_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                    print(f"\n   {next_line.rstrip()}", end='')
                j += 1

    print()  # Final newline


# ----------------------------------------
# CONFIG WIZARD
# ----------------------------------------

def interactive_config_wizard(config_file, current_settings):

    default_settings = {
        'colors': {
            'headword': 'light_green',
            'grammar': 'yellow',
            'match': 'grey',
            'highlight_background': 'yellow'
        },
        'flashcard_count': 10,
        'silent_fail': False,
        'random_word_count': 1,
        'random_headword_count': 1,
        'quiz_word_count': 10,
        'fallback_to_prefix': True
    }
    print("Interactive Configuration Wizard")
    print("Press Enter to keep the current value, or input a new one.\n")
    new_settings = current_settings.copy()

    try:
        # Ensure the config directory exists
        config_dir = os.path.dirname(os.path.expanduser(config_file))
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # Iterate over each configuration option
        for section, options in current_settings.items():
            if isinstance(options, dict):  # For nested sections like colors
                print(f"\nConfiguring section: {section}")
                available_colors = (
                    "black, red, green, yellow, blue, magenta, cyan, white, light_grey, dark_grey, "
                    "light_red, light_green, light_yellow, light_blue, light_magenta, light_cyan"
                )
                for key, value in options.items():
                    default_value = default_settings.get(section, {}).get(key, value)
                    print(f"\nAvailable colors: {available_colors}")
                    new_value = input(f"  {key} [default:{default_value}, currently:{value}]: ") or value
                    new_settings[section][key] = validate_color(new_value)
            else:  # For top-level options
                default_value = default_settings.get(section, options)
                if "count" in section:  # Validate numeric values
                    new_value = input(f"{section} [default:{default_value}, currently:{options}]: ") or options
                    new_settings[section] = validate_numeric(new_value)
                elif isinstance(options, bool):  # Validate True/False flags
                    new_value = input(f"{section} (True/False) [default:{default_value}, currently:{options}]: ") or options
                    new_settings[section] = validate_boolean(new_value)
                else:  # Other options
                    new_value = input(f"{section} [default:{default_value}, currently:{options}]: ") or options
                    new_settings[section] = new_value

        # Save the updated settings to the config file using yaml
        with open(os.path.expanduser(config_file), 'w', encoding='utf-8') as f:
            yaml.dump(new_settings, f, default_flow_style=False, allow_unicode=True)
        print("\nConfiguration saved successfully!")
    except KeyboardInterrupt:
        print("\nConfiguration process canceled. No changes were saved.")

def validate_color(value):
    """Validate if the input is a valid termcolor color."""
    # All available colors in termcolor
    valid_colors = [
        # Text colors
        'grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white',
        # Light text colors
        'light_grey', 'light_red', 'light_green', 'light_yellow', 
        'light_blue', 'light_magenta', 'light_cyan', 'light_white',
        # Dark text colors
        'dark_grey',
        # Extras
        'reset'  # Allow reset as a valid option
    ]
    
    # Convert input to string and lowercase for comparison
    value = str(value).lower().strip()
    
    # Check if it's a valid color
    if value in valid_colors:
        return value
        
    # If not valid, print available options and ask for new input
    print(f"\nInvalid color. Available colors:")
    print("Text colors:", ', '.join(['grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']))
    print("Light colors:", ', '.join(['light_grey', 'light_red', 'light_green', 'light_yellow', 
                                    'light_blue', 'light_magenta', 'light_cyan', 'light_white']))
    print("Dark colors:", 'dark_grey')
    print("Other:", 'reset')
    
    return validate_color(input("Color: "))

def validate_numeric(value):
    """Validate if the input is a valid integer."""
    try:
        return int(value)
    except ValueError:
        print("Invalid number. Please enter a valid integer.")
        return validate_numeric(input("Number: "))
    
def validate_boolean(value):
    """Validate and convert input to a boolean (True/False)."""
    if isinstance(value, bool):
        return value  # Return directly if it's already a boolean
    value = value.lower()
    if value in ['true', 't', 'yes', 'y', '1']:
        return True
    elif value in ['false', 'f', 'no', 'n', '0']:
        return False
    else:
        print("Invalid input. Please enter True or False.")
        return validate_boolean(input("True/False: "))
    
# ----------------------------------------
# FULL TEXT SEARCH WITH %
# ----------------------------------------

def fulltext_search(content, search_term, settings):
    """Handle full-text search with % prefix."""
    main_entry_pattern = r'^\s*[-•]\s+\*?\*?([^\s*]+)(?:\*\*)?(.*?)$'
    subentry_pattern = r'^\s{2,3}\*\*'
    
    matches_to_print = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Process main entries
        if re.match(main_entry_pattern, line):
            match = re.match(main_entry_pattern, line)
            if match:
                head_term = match.group(1).strip('*')
                rest_of_line = match.group(2)
                
                # Check if search term appears in head term or its definition
                if (search_term.lower() in head_term.lower() or 
                    search_term.lower() in rest_of_line.lower()):
                    
                    # Process the headword line
                    if search_term.lower() in head_term.lower():
                        parts = []
                        last_end = 0
                        head_lower = head_term.lower()
                        search_lower = search_term.lower()
                        
                        while True:
                            start = head_lower.find(search_lower, last_end)
                            if start == -1:
                                parts.append(colored(head_term[last_end:], settings['colors']['headword']))
                                break
                            parts.append(colored(head_term[last_end:start], settings['colors']['headword']))
                            matched = head_term[start:start + len(search_term)]
                            parts.append(colored(matched, settings['colors']['match'], 'on_' + settings['colors']['highlight_background']))
                            last_end = start + len(search_term)
                        processed_head = ''.join(parts)
                    else:
                        processed_head = colored(head_term, settings['colors']['headword'])
                    
                    processed_rest = highlight_text(rest_of_line, search_term, settings)
                    matches_to_print.append((i, f"- {processed_head}{processed_rest}"))
                    
                    # Check for matches in sub-entries
                    has_matching_subentries = False
                    j = i + 1
                    subentry_matches = []
                    while j < len(lines) and not re.match(main_entry_pattern, lines[j]):
                        if lines[j].strip():
                            if re.match(subentry_pattern, lines[j]) and search_term.lower() in lines[j].lower():
                                has_matching_subentries = True
                                processed_line = highlight_text(lines[j], search_term, settings)
                                subentry_matches.append((j, processed_line))
                            elif not re.match(subentry_pattern, lines[j]):
                                processed_line = highlight_text(lines[j], search_term, settings)
                                matches_to_print.append((j, processed_line))
                        j += 1
                    if has_matching_subentries:
                        matches_to_print.extend(subentry_matches)
                    i = j - 1
            i += 1
            continue
        
        # Process subentries
        if re.match(subentry_pattern, line):
            if search_term.lower() in line.lower():
                processed_line = highlight_text(line, search_term, settings)
                matches_to_print.append((i, processed_line))
        i += 1
    
    if not matches_to_print:
        if not settings.get('silent_fail', False):
            print(f"No entries found for '{search_term}'")
        return
    
    # Display matches
    current_indent = 0
    for i, line in matches_to_print:
        if line.startswith('   '):
            print(f"\n{line.rstrip()}", end='')
        else:
            if current_indent == 0:
                print()  # Extra line before main entries
            print(f"{line.rstrip()}", end='')
        current_indent = len(line) - len(line.lstrip())

# ----------------------------------------
# ENGLISH SEARCH -e|--english
# ----------------------------------------

def english_search(content, search_term, settings):
    """Search for English words in definitions.
    Only matches full words in non-bold, non-italic text."""
    main_entry_pattern = r'^\s*[-•]\s+\*?\*?([^\s*]+)(?:\*\*)?(.*?)$'
    subentry_pattern = r'^\s{2,3}\*\*'
    
    matches_to_print = []
    lines = content.split('\n')
    i = 0
    
    # Create a pattern that matches the whole word
    word_pattern = r'\b' + re.escape(search_term.lower()) + r'\b'
    
    while i < len(lines):
        line = lines[i]
        
        # Process main entries
        if re.match(main_entry_pattern, line):
            match = re.match(main_entry_pattern, line)
            if match:
                head_term = match.group(1).strip('*')
                rest_of_line = match.group(2)
                
                # Strip out bold and italic text to get English parts
                english_text = rest_of_line
                english_text = re.sub(r'\*\*(.*?)\*\*', '', english_text)  # Remove bold text
                english_text = re.sub(r'\*(.*?)\*', '', english_text)      # Remove italic text
                
                # Check if search term appears as a whole word in English text
                if re.search(word_pattern, english_text.lower()):
                    # Process the headword line
                    processed_head = colored(head_term, settings['colors']['headword'])
                    
                    # Process and highlight the English definition
                    processed_rest = rest_of_line
                    bold_parts = re.findall(r'\*\*(.*?)\*\*', processed_rest)
                    for bold in bold_parts:
                        processed_rest = processed_rest.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                    italic_parts = re.findall(r'\*(.*?)\*', processed_rest)
                    for italic in italic_parts:
                        processed_rest = processed_rest.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                    
                    processed_rest = re.sub(
                        word_pattern,
                        lambda m: colored(m.group(), settings['colors']['match'], 'on_' + settings['colors']['highlight_background']),
                        processed_rest,
                        flags=re.IGNORECASE
                    )
                    
                    matches_to_print.append((i, f"- {processed_head}{processed_rest}"))
                
                # Always check subentries
                j = i + 1
                while j < len(lines) and not re.match(main_entry_pattern, lines[j]):
                    subentry_line = lines[j]
                    if subentry_line.strip() and re.match(subentry_pattern, subentry_line):
                        english_text = subentry_line
                        english_text = re.sub(r'\*\*(.*?)\*\*', '', english_text)
                        english_text = re.sub(r'\*(.*?)\*', '', english_text)
                        
                        if re.search(word_pattern, english_text.lower()):
                            processed_line = subentry_line
                            bold_parts = re.findall(r'\*\*(.*?)\*\*', processed_line)
                            for bold in bold_parts:
                                processed_line = processed_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                            italic_parts = re.findall(r'\*(.*?)\*', processed_line)
                            for italic in italic_parts:
                                processed_line = processed_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                            processed_line = re.sub(
                                word_pattern,
                                lambda m: colored(m.group(), settings['colors']['match'], 'on_' + settings['colors']['highlight_background']),
                                processed_line,
                                flags=re.IGNORECASE
                            )
                            matches_to_print.append((j, processed_line))
                    j += 1
        i += 1
    
    if not matches_to_print:
        if not settings.get('silent_fail', False):
            print(f"No entries found for English word '{search_term}'")
        return
    
    # Display matches
    current_indent = 0
    for i, line in matches_to_print:
        if line.startswith('   '):
            print(f"\n{line.rstrip()}", end='')
        else:
            if current_indent == 0:
                print()  # Extra line before main entries
            print(f"{line.rstrip()}", end='')
        current_indent = len(line) - len(line.lstrip())
    print()  # Final newline


# ----------------------------------------
# DICTIONARY STATISTICS -s --stats Prints a series of statistics about the dataset.
# ----------------------------------------

def print_stats(content):
    """Print statistics about the dictionary content."""
    main_entry_pattern = r'^- '
    subentry_pattern = r'^\s{3}\*\*'
    
    # Initialize counters for detailed stats
    headwords = 0
    subwords = 0
    
    # Word type counters
    subst_total = 0
    subst_m = 0
    subst_f = 0
    subst_mf = 0
    subst_n = 0
    adj_total = 0
    verb_total = 0
    adv_total = 0
    prep_total = 0
    determ_total = 0
    interj_total = 0
    
    # Usage note counters
    usage_counts = {
        'hverdagslig': 0,
        'slang': 0,
        'formelt': 0,
        'dialekt': 0,
        'muntlig': 0,
        'gammeldags': 0,
        'litterært': 0,
        'poetisk': 0,
        'høytidelig': 0,
        'uformelt': 0,
        'spøkefullt': 0,
        'nedsettende': 0,
        'overført': 0
    }
    
    # Domain counters
    domain_counts = {
        'økonomi': 0,
        'jus': 0,
        'medisin': 0,
        'kjemi': 0,
        'matematikk': 0,
        'musikk': 0,
        'botanikk': 0,
        'sport': 0,
        'fysikk': 0,
        'religion': 0,
        'zoologi': 0,
        'data': 0,
        'militær': 0,
        'arkitektur': 0,
        'astronomi': 0,
        'biologi': 0,
        'elektronikk': 0,
        'filosofi': 0,
        'geologi': 0,
        'språkvitenskap': 0,
        'handel': 0,
        'landbruk': 0,
        'meteorologi': 0,
        'pedagogikk': 0,
        'petroleum': 0,
        'psykologi': 0,
        'regnskap': 0,
        'sjøfart': 0,
        'sosiologi': 0,
        'statistikk': 0,
        'teknologi': 0,
        'tollvesen': 0,
        'veterinærmedisin': 0
    }
    
    # Initialize letter-specific counters
    class LetterStats:
        def __init__(self):
            self.total = 0
            self.nouns = 0
            self.verbs = 0
            self.adj = 0
            self.adv = 0
            self.other = 0
            self.unknown = 0
    
    # Initialize stats for each letter
    letter_stats = {}
    norwegian_alphabet = 'abcdefghijklmnopqrstuvwxyzæøå'
    for letter in norwegian_alphabet:
        letter_stats[letter] = LetterStats()
    
    # Initialize word lengths
    word_lengths = {i: 0 for i in range(1, 21)}  # 1-20 chars
    
    # Counter for entries with examples
    entries_with_examples = 0
    current_entry_has_example = False
    
    # Process the content
    lines = content.split('\n')
    current_line = 0
    
    while current_line < len(lines):
        line = lines[current_line]
        
        if re.match(main_entry_pattern, line):
            headwords += 1
            if current_entry_has_example:
                entries_with_examples += 1
            current_entry_has_example = False
            
            word_match = re.search(r'\*\*([^*]+)\*\*', line)
            if word_match:
                word = word_match.group(1)
                first_letter = word[0].lower() if word else ''
                
                # Word length statistics
                length = len(word)
                if length <= 20:
                    word_lengths[length] += 1
                    
                if first_letter in letter_stats:
                    stats = letter_stats[first_letter]
                    stats.total += 1
                    
                    # Remove all asterisks to simplify pattern matching
                    clean_line = line.replace('*', '')
                    
                    # Check for usage notes and domains
                    lower_line = line.lower()
                    for note in usage_counts:
                        if f'*({note})*' in lower_line:
                            usage_counts[note] += 1
                    
                    for domain in domain_counts:
                        if f'*({domain})*' in lower_line:
                            domain_counts[domain] += 1
                    
                    # Check for nouns and their genders
                    if 'subst.' in clean_line:
                        subst_total += 1
                        stats.nouns += 1
                        if re.search(r'subst\.\s*m/f\b', clean_line):
                            subst_mf += 1
                        elif re.search(r'subst\.\s*m\b', clean_line):
                            subst_m += 1
                        elif re.search(r'subst\.\s*f\b', clean_line):
                            subst_f += 1
                        elif re.search(r'subst\.\s*n\b', clean_line):
                            subst_n += 1
                    
                    # Check other word types
                    elif 'adj.' in clean_line:
                        adj_total += 1
                        stats.adj += 1
                    elif 'verb' in clean_line:
                        verb_total += 1
                        stats.verbs += 1
                    elif 'adv.' in clean_line:
                        adv_total += 1
                        stats.adv += 1
                    elif 'prep.' in clean_line:
                        prep_total += 1
                        stats.other += 1
                    elif 'determ.' in clean_line:
                        determ_total += 1
                        stats.other += 1
                    elif 'interj.' in clean_line:
                        interj_total += 1
                        stats.other += 1
                    else:
                        stats.unknown += 1
        
        elif re.match(subentry_pattern, line):
            subwords += 1
            # Count usage notes and domains in subentries too
            lower_line = line.lower()
            for note in usage_counts:
                if f'*({note})*' in lower_line:
                    usage_counts[note] += 1
            
            for domain in domain_counts:
                if f'*({domain})*' in lower_line:
                    domain_counts[domain] += 1
        
        # Check for examples (lines with bullet points and English translations)
        if '•' in line:
            current_entry_has_example = True
            
        current_line += 1
    
    # Calculate totals
    nouns_with_gender = subst_m + subst_f + subst_mf + subst_n
    total_word_types = (subst_total + adj_total + verb_total + adv_total + 
                       prep_total + determ_total + interj_total)
    
    # Print original detailed statistics
    print("\nDictionary Statistics")
    print(f"\nTotal headwords: {headwords}")
    print(f"Total subentries: {subwords}")
    
    print("\nWord Types:")
    print(f"Total words with identified type: {total_word_types} ({round(total_word_types/headwords * 100)}% of headwords)")
    print(f"\nNouns (subst.): {subst_total} ({round(subst_total/headwords * 100)}% of headwords)")
    print(f"  Nouns with identified gender: {nouns_with_gender} ({round(nouns_with_gender/subst_total * 100)}% of nouns)")
    print(f"    Masculine (subst. m): {subst_m} ({round(subst_m/nouns_with_gender * 100)}% of gendered nouns)")
    print(f"    Feminine (subst. f): {subst_f} ({round(subst_f/nouns_with_gender * 100)}% of gendered nouns)")
    print(f"    Common gender (subst. m/f): {subst_mf} ({round(subst_mf/nouns_with_gender * 100)}% of gendered nouns)")
    print(f"    Neuter (subst. n): {subst_n} ({round(subst_n/nouns_with_gender * 100)}% of gendered nouns)")
    print(f"  Nouns without gender: {subst_total - nouns_with_gender}")
    
    print(f"\nAdjectives (adj.): {adj_total} ({round(adj_total/headwords * 100)}% of headwords)")
    print(f"Verbs (verb): {verb_total} ({round(verb_total/headwords * 100)}% of headwords)")
    print(f"Adverbs (adv.): {adv_total} ({round(adv_total/headwords * 100)}% of headwords)")
    print(f"Prepositions (prep.): {prep_total} ({round(prep_total/headwords * 100)}% of headwords)")
    print(f"Determiners (determ.): {determ_total} ({round(determ_total/headwords * 100)}% of headwords)")
    print(f"Interjections (interj.): {interj_total} ({round(interj_total/headwords * 100)}% of headwords)")
    
    print("\nCoverage Analysis:")
    print(f"Words with unidentified type: {headwords - total_word_types} ({round((headwords - total_word_types)/headwords * 100)}% of headwords)")
    
    # Print word length distribution
    print("\nWord Length Distribution")
    print("-" * 40)
    max_count = max(word_lengths.values())
    bar_length = 30
    for length, count in word_lengths.items():
        if count > 0:
            percentage = count/headwords*100
            bars = int((count/max_count) * bar_length)
            print(f"{length:2d} chars: {count:6d} ({percentage:4.1f}%) {'#' * bars}")

    # Print Usage Notes
    print("\nUsage Notes")
    print("-" * 40)
    for usage, count in sorted(usage_counts.items(), key=lambda x: (-x[1], x[0])):
        if count >= 10:  # Only show if 10 or more entries
            percentage = round(count / headwords * 100, 1)
            print(f"{usage:<12}: {count:>6} ({percentage:>4.1f}%)")
    
    # Print Domain-Specific Terms
    print("\nDomain-Specific Terms")
    print("-" * 40)
    for domain, count in sorted(domain_counts.items(), key=lambda x: (-x[1], x[0])):
        if count >= 10:  # Only show if 10 or more entries
            percentage = round(count / headwords * 100, 1)
            print(f"{domain:<12}: {count:>6} ({percentage:>4.1f}%)")
    
    print("\nWord Type Distribution by Letter")
    print("\n{:<8} {:>13} {:>13} {:>13} {:>13} {:>13} {:>13} {:>13}".format("Letter", "Total (%)", "Nouns (%)", "Verbs (%)", "Adj (%)", "Adv (%)", "Other (%)", "Unknown (%)"))
    print("-" * 110)
    
    # Filter and sort letters that have entries
    active_letters = [(letter, stats) for letter, stats in letter_stats.items() 
                     if stats.total > 0]
    active_letters.sort(key=lambda x: (-x[1].total, x[0]))
    
    for letter, stats in active_letters:
        if stats.total > 0:
            print("{:<8} {:>5} ({:4.1f}%) {:>5} ({:4.1f}%) {:>5} ({:4.1f}%) {:>5} ({:4.1f}%) {:>5} ({:4.1f}%) {:>5} ({:4.1f}%) {:>5} ({:4.1f}%)".format(
                letter.upper() + ":",
                stats.total, stats.total/headwords*100,
                stats.nouns, stats.nouns/stats.total*100,
                stats.verbs, stats.verbs/stats.total*100,
                stats.adj, stats.adj/stats.total*100,
                stats.adv, stats.adv/stats.total*100,
                stats.other, stats.other/stats.total*100,
                stats.unknown, stats.unknown/stats.total*100
            ))

    print("-" * 110)
    
    totals = LetterStats()
    for stats in letter_stats.values():
        totals.total += stats.total
        totals.nouns += stats.nouns
        totals.verbs += stats.verbs
        totals.adj += stats.adj
        totals.adv += stats.adv
        totals.other += stats.other
        totals.unknown += stats.unknown
    
    print("{:<8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}".format(
        "TOTAL:",
        totals.total,
        totals.nouns,
        totals.verbs,
        totals.adj,
        totals.adv,
        totals.other,
        totals.unknown
    ))
    if totals.total > 0:
        print("{:<8} {:>7.1f}% {:>7.1f}% {:>7.1f}% {:>7.1f}% {:>7.1f}% {:>7.1f}% {:>7.1f}%".format(
            "",
            100.0,  # Always 100% of total
            totals.nouns/totals.total*100,
            totals.verbs/totals.total*100,
            totals.adj/totals.total*100,
            totals.adv/totals.total*100,
            totals.other/totals.total*100,
            totals.unknown/totals.total*100
        ))
    
    # Print example sentence statistics
    print(f"\nEntries with Examples: {entries_with_examples} ({entries_with_examples/headwords*100:.1f}% of total entries)")

# ----------------------------------------
# LIST CATEGORY
# ----------------------------------------

def list_category(content, settings, category):
    """List all words in a given category."""
    main_entry_pattern = r'^- '
    matches = []
    lines = content.split('\n')
    i = 0
    
    # Handle random count
    count = None
    is_random = False
    if category == 'r':
        count = 1
        is_random = True
    elif category.startswith('r') and len(category) > 1:
        try:
            count = int(category[1:])
            is_random = True
        except ValueError:
            print(f"Error: Invalid random count in '{category}'")
            return
    
    while i < len(lines):
        line = lines[i]
        if re.match(main_entry_pattern, line):
            word_match = re.search(r'\*\*([^*]+)\*\*', line)
            is_match = False
            
            if word_match:
                # For random category, match any word
                if is_random:
                    is_match = True
                elif category == 'm' and re.search(r'\*subst\.\s*m\*', line):
                    is_match = True
                elif category == 'f' and re.search(r'\*subst\.\s*f\*', line):
                    is_match = True
                elif category == 'c' and re.search(r'\*subst\.\s*m/f\*', line):
                    is_match = True
                elif category == 'n' and re.search(r'\*subst\.\s*n\*', line):
                    is_match = True
                elif category == 'adj' and re.search(r'\*adj\.\*', line):
                    is_match = True
                elif category == 'v' and re.search(r'\*verb\*', line):
                    is_match = True
                elif category == 'adv' and re.search(r'\*adv\.\*', line):
                    is_match = True
                elif category == 'u':
                    has_type = any(type_pattern in line for type_pattern in 
                                 [r'\*subst\.', r'\*adj\.', r'\*verb\*', r'\*adv\.'])
                    is_match = not has_type
                elif category == 'w':
                    is_noun = re.search(r'\*subst\.\*', line)
                    has_gender = any(gender_pattern in line for gender_pattern in 
                                   [r'\*subst\.\s*m\*', r'\*subst\.\s*f\*', 
                                    r'\*subst\.\s*m/f\*', r'\*subst\.\s*n\*'])
                    is_match = is_noun and not has_gender
            
            if is_match:
                entry_lines = [i]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if re.match(r'^- ', next_line):
                        break
                    if next_line.strip():
                        entry_lines.append(j)
                    j += 1
                matches.append((word_match.group(1).lower(), entry_lines))
        i += 1
    
    if not matches:
        if not settings.get('silent_fail', False):
            print(f"No entries found for category '{category}'")
        return
    
    # For random selection
    if is_random:
        import random
        count = count if count else 1
        if count > len(matches):
            count = len(matches)
        matches = random.sample(matches, count)
    else:
        # Sort alphabetically, putting æøå at the end
        def sort_key(word_tuple):
            word = word_tuple[0]
            word = word.replace('æ', 'zz1').replace('ø', 'zz2').replace('å', 'zz3')
            return word
        matches.sort(key=lambda x: sort_key(x))
    
    # Display matches using search_dictionary's display logic
    is_first_entry = True
    for _, line_numbers in matches:
        for line_num in line_numbers:
            line = lines[line_num]
            if line.startswith('- '):
                if not is_first_entry:
                    print()
                else:
                    is_first_entry = False
                
                word_match = re.search(r'\*\*(.*?)\*\*', line)
                head_term = word_match.group(1) if word_match else ''
                rest_of_line = line[line.find('**' + head_term + '**') + len('**' + head_term + '**'):]
                
                # Format the output
                bold_parts = re.findall(r'\*\*(.*?)\*\*', rest_of_line)
                for bold in bold_parts:
                    rest_of_line = rest_of_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                italic_parts = re.findall(r'\*(.*?)\*', rest_of_line)
                for italic in italic_parts:
                    rest_of_line = rest_of_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                
                print(f"- {colored(head_term, settings['colors']['headword'])}{rest_of_line}", end='')
            else:
                # Format subentry
                bold_parts = re.findall(r'\*\*(.*?)\*\*', line)
                for bold in bold_parts:
                    line = line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                italic_parts = re.findall(r'\*(.*?)\*', line)
                for italic in italic_parts:
                    line = line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                print(f"\n   {line.rstrip()}", end='')
    
    print()  # Final newline

# ----------------------------------------
# RANDOM WORDS -r
# ----------------------------------------

def get_random_words(content, settings, count=1):
    """Get random words from the dictionary."""
    main_entry_pattern = r'^- '
    matches = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if re.match(main_entry_pattern, line):
            word_match = re.search(r'\*\*([^*]+)\*\*', line)
            if word_match:
                entry_lines = [i]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if re.match(r'^- ', next_line):
                        break
                    if next_line.strip():
                        entry_lines.append(j)
                    j += 1
                matches.append((word_match.group(1).lower(), entry_lines))
        i += 1
    
    if not matches:
        if not settings.get('silent_fail', False):
            print("No entries found in dictionary")
        return
    
    # Select random entries
    import random
    if count > len(matches):
        count = len(matches)
    matches = random.sample(matches, count)
    
    # Display matches
    is_first_entry = True
    for _, line_numbers in matches:
        for line_num in line_numbers:
            line = lines[line_num]
            if line.startswith('- '):
                if not is_first_entry:
                    print()
                else:
                    is_first_entry = False
                
                word_match = re.search(r'\*\*(.*?)\*\*', line)
                head_term = word_match.group(1) if word_match else ''
                rest_of_line = line[line.find('**' + head_term + '**') + len('**' + head_term + '**'):]
                
                # Format the output
                bold_parts = re.findall(r'\*\*(.*?)\*\*', rest_of_line)
                for bold in bold_parts:
                    rest_of_line = rest_of_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                italic_parts = re.findall(r'\*(.*?)\*', rest_of_line)
                for italic in italic_parts:
                    rest_of_line = rest_of_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                
                print(f"- {colored(head_term, settings['colors']['headword'])}{rest_of_line}", end='')
            else:
                # Format subentry
                bold_parts = re.findall(r'\*\*(.*?)\*\*', line)
                for bold in bold_parts:
                    line = line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                italic_parts = re.findall(r'\*(.*?)\*', line)
                for italic in italic_parts:
                    line = line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                print(f"\n   {line.rstrip()}", end='')
    
    print()  # Final newline

# ----------------------------------------
# RANDOM HEADWORDS -R (no definitions)
# ----------------------------------------

def get_random_headwords(content, settings, count=1):
    """Get just the headwords of random words from the dictionary."""
    main_entry_pattern = r'^- '
    matches = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if re.match(main_entry_pattern, line):
            word_match = re.search(r'\*\*([^*]+)\*\*', line)
            if word_match:
                matches.append(word_match.group(1))
        i += 1
    
    if not matches:
        if not settings.get('silent_fail', False):
            print("No entries found in dictionary")
        return
    
    # Select random entries
    if count > len(matches):
        count = len(matches)
    selected = random.sample(matches, count)
    
    # Print just the headwords, one per line
    for word in selected:
        print(word)
# ----------------------------------------
# RUN FLASHCARDS -f|--flash
# ----------------------------------------

def run_flashcards(content, settings, count=10):
    """Run an interactive quiz with the specified number of words."""
    main_entry_pattern = r'^- '
    entries = []
    lines = content.split('\n')
    i = 0
    
    # Collect all entries
    while i < len(lines):
        line = lines[i]
        if re.match(main_entry_pattern, line):
            word_match = re.search(r'\*\*([^*]+)\*\*', line)
            if word_match:
                entry_lines = [i]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if re.match(r'^- ', next_line):
                        break
                    if next_line.strip():
                        entry_lines.append(j)
                    j += 1
                entries.append((word_match.group(1), entry_lines))
        i += 1
    
    if not entries:
        if not settings.get('silent_fail', False):
            print("No entries found in dictionary")
        return
    
    # Select random entries
    if count > len(entries):
        count = len(entries)
    quiz_entries = random.sample(entries, count)
    not_remembered = quiz_entries.copy()
    
    round_num = 1
    while not_remembered:
        print(f"\nRound {round_num} - {len(not_remembered)} words remaining")
        print("Press any key to show definition, SPACE to mark correct, BACKSPACE/DELETE to keep reviewing. Ctrl+C to exit.")
        time.sleep(0.5)
        
        # Shuffle the remaining words
        random.shuffle(not_remembered)
        still_learning = []
        
        for head_term, line_numbers in not_remembered:
            # Show just the headword first
            print(f"\nWord: {colored(head_term, settings['colors']['headword'])}")
            
            # Wait for ENTER or any key to show definition
            ch = get_char()
            if ch == '\x03':  # Ctrl+C
                print("\nQuiz terminated.")
                return
            
            # Show the full entry
            print("\nDefinition:")
            for line_num in line_numbers:
                line = lines[line_num]
                if line.startswith('- '):
                    word_match = re.search(r'\*\*(.*?)\*\*', line)
                    if word_match:
                        rest_of_line = line[line.find('**' + head_term + '**') + len('**' + head_term + '**'):]
                        
                        # Format the output
                        bold_parts = re.findall(r'\*\*(.*?)\*\*', rest_of_line)
                        for bold in bold_parts:
                            rest_of_line = rest_of_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                        italic_parts = re.findall(r'\*(.*?)\*', rest_of_line)
                        for italic in italic_parts:
                            rest_of_line = rest_of_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                        
                        print(f"- {colored(head_term, settings['colors']['headword'])}{rest_of_line}")
                else:
                    # Format subentry
                    formatted_line = line
                    bold_parts = re.findall(r'\*\*(.*?)\*\*', formatted_line)
                    for bold in bold_parts:
                        formatted_line = formatted_line.replace(f'**{bold}**', colored(bold, settings['colors']['headword']))
                    italic_parts = re.findall(r'\*(.*?)\*', formatted_line)
                    for italic in italic_parts:
                        formatted_line = formatted_line.replace(f'*{italic}*', colored(italic, settings['colors']['grammar']))
                    print(f"   {formatted_line.rstrip()}")
            
            # Get user response
            while True:
                ch = get_char()
                if ch == ' ':  # SPACE
                    print(colored("\n✓ Marked as remembered", 'green'))
                    break
                elif ch in ('\x7f', '\x08'):  # BACKSPACE/DELETE
                    print(colored("\n× Marked for review", 'yellow'))
                    still_learning.append((head_term, line_numbers))
                    break
                elif ch == '\x03':  # Ctrl+C
                    print("\nQuiz terminated.")
                    return
            
            print("\n" + "─" * 40)  # Separator line
        
        not_remembered = still_learning
        round_num += 1
    
    print(colored("\nCongratulations! You've learned all the words!", 'green'))

# ----------------------------------------
# RUN TESTS -t
# ----------------------------------------

def run_tests(content, test_term, settings):
    """Run test searches.
    
    If test_term is provided, do a raw text search for that exact headword.
    Otherwise run the default test searches.
    """
    if test_term:
        # Do raw text search for exact headword
        lines = content.split('\n')
        found = False
        entry_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith(f'- **{test_term}'):
                found = True
                entry_lines.append(line)
                
                # Collect any sub-entries (indented lines)
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.startswith('- '):
                        break
                    if next_line.strip():
                        entry_lines.append(next_line)
                    j += 1
                break
                
        if found:
            print("\n".join(entry_lines))
        else:
            print(f"No exact match found for '{test_term}'")
            
    else:
        # Run default test searches
        test_terms = ['hus', 'husm', '@nasjonal', 'nasjonal@', '%gude']
        
        print("Running test searches...\n")
        for term in test_terms:
            print(f"\n=== Testing search: '{term}' ===\n")
            search_dictionary(content, term, settings)
            print("\n")


# NEW QUIZ FUNCTION -q|--quiz

# Used for -q feature:
def get_clean_definition(line):
    """Extract clean English definition from a headword entry line."""
    # Get text after the headword
    parts = line.split('**', 2)
    if len(parts) < 3:
        return None
        
    definition = parts[2]
    
    # Remove italic grammar/usage notes
    definition = re.sub(r'\*(.*?)\*', '', definition)
    
    # Remove any remaining asterisks
    definition = definition.replace('*', '')
    
    # Remove leading/trailing whitespace and bullet points
    definition = definition.strip('- •\t\n\r')
    
    return definition.strip()

# Used for -q feature:
def get_headword_entries(content):
    """Get all headwords and their definitions, excluding subentries."""
    entries = []
    main_entry_pattern = r'^\s*[-•]\s+\*\*([^*]+)\*\*'
    
    lines = content.split('\n')
    for line in lines:
        if re.match(main_entry_pattern, line):
            headword = re.search(r'\*\*([^*]+)\*\*', line).group(1)
            definition = get_clean_definition(line)
            if definition:  # Only add entries with valid definitions
                entries.append((headword, definition))
    
    return entries

# Used for -q feature:
def get_short_wrong_definitions(all_entries, correct_def, num_needed=4, max_words=15):
    """Get random wrong definitions that are shorter than max_words."""
    # Filter entries to only include definitions with less than max_words
    short_entries = [e for e in all_entries 
                    if e[1] != correct_def and 
                    len(e[1].split()) <= max_words]
    
    if len(short_entries) < num_needed:
        # If we don't have enough short entries, use longer ones as backup
        remaining_entries = [e for e in all_entries if e[1] != correct_def]
        short_entries.extend(remaining_entries)
    
    # Select random entries from our pool
    selected = random.sample(short_entries, min(num_needed, len(short_entries)))
    return [entry[1] for entry in selected]

def run_quiz(content, settings, count=10):
    """Run an interactive multiple choice quiz."""
    # Get all valid headword entries
    all_entries = get_headword_entries(content)
    if len(all_entries) < 6:  # Need at least 6 entries (1 correct + 5 wrong options)
        print("Error: Not enough dictionary entries for quiz")
        return
        
    # Select random words for the quiz
    if count > len(all_entries):
        count = len(all_entries)
    quiz_entries = random.sample(all_entries, count)
    not_learned = quiz_entries.copy()
    
    round_num = 1
    while not_learned:
        print(f"\nRound {round_num} - {len(not_learned)} words remaining")
        print("Press any key to show options, or Ctrl+C to exit.")
        time.sleep(0.5)
        
        # Shuffle remaining words
        random.shuffle(not_learned)
        still_learning = []
        
        for headword, correct_def in not_learned:
            # Show the headword
            print(f"\nWord: {colored(headword, settings['colors']['headword'])}")
            
            # Wait for key press
            ch = get_char()
            if ch == '\x03':  # Ctrl+C
                print("\nQuiz terminated.")
                return
            
            # Get 4 random wrong definitions (now using the new function)
            wrong_defs = get_short_wrong_definitions(all_entries, correct_def)
            
            # Create answer options
            options = wrong_defs + [correct_def]
            random.shuffle(options)
            correct_letter = 'abcde'[options.index(correct_def)]
            
            # Display options
            print("\nChoose the correct definition:")
            for i, opt in enumerate(options):
                print(f"{chr(97 + i)}) {opt}")
            
            # Get user's answer
            while True:
                print("\nYour answer (a/b/c/d/e):", end=' ', flush=True)
                ch = get_char().lower()
                print(ch)  # Echo the character
                
                if ch == '\x03':  # Ctrl+C
                    print("\nQuiz terminated.")
                    return
                if ch in 'abcde':
                    break
                print("Please enter a, b, c, d, or e")
            
            # Check answer
            if ch == correct_letter:
                print(colored("\n✓ Correct!", 'green'))
            else:
                print(colored("\n× Incorrect", 'red'))
                print(f"The correct answer was {correct_letter}) {correct_def}")
                still_learning.append((headword, correct_def))
            
            print("\n" + "─" * 40)  # Separator line
        
        not_learned = still_learning
        round_num += 1
    
    print(colored("\nCongratulations! You've learned all the words!", 'green'))

def main():
    # Load configuration and settings
    settings = get_settings()

    # Handle piped input from stdin
    if not sys.stdin.isatty():
        settings['fallback_to_prefix'] = False # don't fall back to prefix search if no entries are found
        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()

        for line in sys.stdin:
            search_term = line.strip()
            if search_term:
                search_dictionary(content, search_term, settings)
        return

    # Handle english search command:
    if len(sys.argv) >= 2 and sys.argv[1] in ['-e', '--english']:
        if len(sys.argv) < 3:
            print("Error: Search term required for English search")
            sys.exit(1)

        search_term = sys.argv[2]
        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        english_search(content, search_term, settings)
        return

    # Handle quiz command:
    if len(sys.argv) == 2 and (sys.argv[1].startswith('-q') or sys.argv[1].startswith('--quiz')):
        count = settings['quiz_word_count']
        try:
            num_part = sys.argv[1].replace('-q', '').replace('--quiz', '')
            if num_part:
                count = int(num_part)
        except ValueError:
            print("Error: Invalid quiz count")
            sys.exit(1)

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        run_quiz(content, settings, count)
        return

    # Handle flashcard command:
    if len(sys.argv) == 2 and (sys.argv[1].startswith('-f') or sys.argv[1].startswith('--flash')):
        count = settings['flashcard_count']
        try:
            num_part = sys.argv[1].replace('-f', '').replace('--flash', '')
            if num_part:
                count = int(num_part)
        except ValueError:
            print("Error: Invalid flashcard count")
            sys.exit(1)

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        run_flashcards(content, settings, count)
        return
    
    # Handle exact match sample sentences from Tatoeba list with -s
    if len(sys.argv) >= 3 and sys.argv[1] in ['-x', '--examples']:
        search_term = sys.argv[2]

        # Regular search (headword, definition, sub-entries, etc.)
        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        search_dictionary(content, search_term, settings)

        # Blank line after regular search
        print("")

        # Exact match search in sentences.tsv
        try:
            with resources.open_text('nordic.data', 'sentences.tsv') as tsvfile:
                matches_found = False
                print("Sentences from Tatoeba database:\n")

                for line in tsvfile:
                    columns = line.strip().split('\t')
                    if len(columns) >= 3 and re.search(rf'\b{re.escape(search_term)}\b', columns[2]):
                        highlighted_sentence = highlight_match(columns[2], '@' + search_term, settings, True)
                        print("- " + highlighted_sentence)  # Output the highlighted sentence
                        matches_found = True

                if not matches_found:
                    print(f"No exact matches found for '{search_term}' in sentences.tsv.")
        except FileNotFoundError:
            print("Error: sentences.tsv not found.")
        
        return


    # Handle random words
    if len(sys.argv) == 2 and (sys.argv[1].startswith('-r') or sys.argv[1].startswith('--random')):
        count = settings['random_word_count']
        try:
            num_part = sys.argv[1].replace('-r', '').replace('--random', '')
            if num_part:
                count = int(num_part)
        except ValueError:
            print("Error: Invalid random count")
            sys.exit(1)

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        get_random_words(content, settings, count)
        return

    # Handle random headwords command
    if len(sys.argv) == 2 and sys.argv[1].startswith('-R'):
        count = settings['random_headword_count']
        try:
            num_part = sys.argv[1].replace('-R', '')
            if num_part:
                count = int(num_part)
        except ValueError:
            print("Error: Invalid random count")
            sys.exit(1)

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        get_random_headwords(content, settings, count)
        return

    # Handle config wizard -c
    if len(sys.argv) == 2 and sys.argv[1] in ['-c', '--config']:
        config_file = "~/.config/nordic/config.yaml"  # Update with the correct path
        current_settings = get_settings()  # Assuming this function loads your current settings
        interactive_config_wizard(config_file, current_settings)
        return

    # Handle test command
    if len(sys.argv) >= 2 and sys.argv[1] in ['-t', '--test']:
        test_term = sys.argv[2] if len(sys.argv) > 2 else None

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        run_tests(content, test_term, settings)
        return

    # Handle stats
    if len(sys.argv) == 2 and sys.argv[1] in ['--stats', '-s']:
        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        print_stats(content)
        return

    # Handle list
    if len(sys.argv) >= 2 and sys.argv[1] in ['-l', '--list']:
        if len(sys.argv) < 3:
            print("Error: Category required for list command")
            print("Categories: m, f, c, n, w, adj, v, adv, u")
            sys.exit(1)

        category = sys.argv[2]
        if category not in ['m', 'f', 'c', 'n', 'w', 'adj', 'v', 'adv', 'u']:
            print("Error: Invalid category")
            print("Categories: m, f, c, n, w, adj, v, adv, u")
            sys.exit(1)

        with resources.open_text('nordic.data', 'combined.md') as file:
            content = file.read()
        list_category(content, settings, category)
        return

    # Handle regular search
    if len(sys.argv) != 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        sys.exit(1)

    search_term = sys.argv[1]
    with resources.open_text('nordic.data', 'combined.md') as file:
        content = file.read()
    search_dictionary(content, search_term, settings)

    
if __name__ == "__main__":
    main()
