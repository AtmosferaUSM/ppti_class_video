##### This script cleans up script.txt so that the tts can works correctly #####

import re
import shutil 
#import contractions


def normalize_scientific_text(text):
    # 1. Expand English contractions
    #text = contractions.fix(text)

    # 2. Abbreviation replacements with space-separated uppercase letters (no dots)
    abbreviation_map = {                
        #'Inc.': 'I N C', 
        #'Ltd.': 'L T D',
        #'No.': 'N O',                 
        #'et al.': 'E T A L',
        #'ibid.': 'I B I D', 
        #'op. cit.': 'O P C I T',        
        #'loc. cit.': 'L O C C I T',
        ##'Dept.': 'D E P T', 
        #'Univ.': 'U N I V', 
        #'Vol.': 'V O L', 
        
        #'Trans.': 'T R A N S', 
        'Ser.': 'S E R', 
        'Bk.': 'B K',
        'Fig.': 'F I G',         
        'Ref.': 'R E F', 
        'e.g.': 'E G', 
        'i.e.': 'I E',
        'etc.': 'E T C', 
        'U.S.': 'U S', 
        'U.K.': 'U K', 
    }
    for abbr in sorted(abbreviation_map, key=len, reverse=True):
        pattern = r'\b' + re.escape(abbr) + r'\b'
        text = re.sub(pattern, abbreviation_map[abbr], text)

    # Original two-letter US state abbreviations
    us_states = [
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'
    ]

    # Step 1: Create lowercase, space-separated, quoted form: ' c o ', etc.
    us_state_map = {
    abbr: f"' {abbr[0].lower()} {abbr[1].lower()} '"
    for abbr in us_states}

    # Step 2: Replace spaced versions (e.g., "C O" → "' c o '")
    for abbr in us_states:
        spaced_pattern = rf"\b{abbr[0]}\s+{abbr[1]}\b"
        replacement = f"' {abbr[0].lower()} {abbr[1].lower()} '"
        text = re.sub(spaced_pattern, replacement, text)

    # Step 3: Replace compact versions (e.g., "CO" → "' c o '")
    for abbr in sorted(us_state_map, key=len, reverse=True):
        pattern = rf"\b{abbr}\b"
        text = re.sub(pattern, us_state_map[abbr], text)

    # 4. Chemical elements
    elements = [
        'H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar','K','Ca','Sc','Ti',
        'V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr','Rb','Sr','Y','Zr','Nb','Mo',
        'Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe','Cs','Ba','La','Ce','Pr','Nd','Pm','Sm',
        'Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu','Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb',
        'Bi','Po','At','Rn','Fr','Ra','Ac','Th','Pa','U','Np','Pu','Am','Cm','Bk','Cf','Es','Fm','Md','No',
        'Lr','Rf','Db','Sg','Bh','Hs','Mt','Ds','Rg','Cn','Nh','Fl','Mc','Lv','Ts','Og',   
    ]
    element_map = {el: ' '.join(el) for el in elements}
    #element_map['U'] = "'u'"
    #element_map['V'] = "'v'"
    
    for el in sorted(element_map, key=len, reverse=True):
        pattern = r'\b' + re.escape(el) + r'\b'
        text = re.sub(pattern, element_map[el], text)

    # 5. Force standalone U or V even with punctuation
    text = re.sub(r'\bU(?=\W|$)', "'u'", text)
    text = re.sub(r'\bV(?=\W|$)', "'v'", text)
    text = re.sub(r'\bv(?=\W|$)', "'v'", text)
    text = re.sub(r'\bo(?=\W|$)', "' o '", text)
    text = re.sub(r'\bO(?=\W|$)', "' o '", text)
    text = re.sub(r'\bDr(?=\W|$)', "'D' 'r'", text)
    text = re.sub(r'\bDR(?=\W|$)', "'D' 'R'", text)
    text = re.sub(r'\bMr(?=\W|$)', "'M' 'R'", text)
    text = re.sub(r'\bMR(?=\W|$)', "'M' 'R'", text)
    text = re.sub(r'\bMs(?=\W|$)', "'M' 'S'", text)
    text = re.sub(r'\bMrs(?=\W|$)', "'M' 'R' 'S'", text)
    text = re.sub(r'\bST(?=\W|$)', "'S' 'T'", text)
    text = re.sub(r'\bSt(?=\W|$)', "'S' 'T'", text)
    text = re.sub(r'\bEq(?=\W|$)', "'E' 'Q'", text)
    text = re.sub(r'\bEQ(?=\W|$)', "'E' 'Q'", text)
    text = re.sub(r'\bvs(?=\W|$)', "'v' 'S'", text)
    text = re.sub(r'\bVs(?=\W|$)', "'v' 'S'", text)
    text = re.sub(r'\bVS(?=\W|$)', "'v' 'S'", text)
    text = re.sub(r'\bp(?=\W|$)', "'P' ", text)
    text = re.sub(r'\bpp(?=\W|$)', "'P' 'P'", text)
    text = re.sub(r'\bCo(?=\W|$)', "' c ' ' o '", text)
    text = re.sub(r'\bco(?=\W|$)', "' c ' ' o '", text)
    text = re.sub(r'\bca(?=\W|$)', "' c ' 'A'", text)
    text = re.sub(r'\bcf(?=\W|$)', "' c ' 'F'", text)
    text = re.sub(r'\bop(?=\W|$)', "' o ' 'P'", text)
    text = re.sub(r'\bed(?=\W|$)', "'E' 'D'", text)
    text = re.sub(r'\beds(?=\W|$)', "'E' 'D' 'S' ", text)
    text = re.sub(r'\bRev(?=\W|$)', "'E' 'E' 'v' ", text)
    text = re.sub(r'\bch(?=\W|$)', "'C' 'H' ", text)
    text = re.sub(r'\bCH(?=\W|$)', "'C' 'H' ", text)
    text = re.sub(r'\bCh(?=\W|$)', "'C' 'H' ", text)
    text = re.sub(r'\bst(?=\W|$)', "' s ' ' t ' ", text)
    text = re.sub(r'\bnd(?=\W|$)', "' n ' ' d ' ", text)
    text = re.sub(r'\brd(?=\W|$)', "' r ' ' d ' ", text)
    text = re.sub(r"\b[vV]([0-9]+(?:\.[0-9]+)?)(?=\W|$)", r"'v' \1", text)
    text = re.sub('\u2013', '-', text)
    text = re.sub(r"(?<!\*)[\u0080-\uFFFF](?!\*)", "", text)
    text = re.sub(r"[ˋ’ʿʻ]", "`", text)
    text = re.sub(r"`", "'", text)
    text = re.sub(r'\bI\s+n\b', 'in', text)
    text = re.sub(r'\bA\s+s\b', 'as', text)
    text = text.replace("''", "'")
        
    
    # 6. Replace calculus differentials (e.g. dy → d 'y')
    for var in ['x','y','z','v','r','s','t','a','b','c','e','i','u']:
        pattern = rf'\bd{var}(?=\W|$)'
        text = re.sub(pattern, f"d '{var}'", text)

    return text

# === Read from script.txt, process, write to script_cleaned.txt ===
input_file = 'script.txt'
backup_file = 'orig_script.txt'
# Backup original
shutil.copyfile(input_file, backup_file)

# Read input
import chardet

with open('script.txt', 'rb') as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']

with open('script.txt', 'r', encoding=encoding) as f:
    content = f.read()
    
#with open(input_file, 'r', encoding='utf-8') as f:
#    content = f.read()

# Normalize text
cleaned = normalize_scientific_text(content)

output_file = 'script.txt'
# Write output
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(cleaned)

#scriptfile = 'script.txt'
#normalize_scientific_text(scriptfile)
