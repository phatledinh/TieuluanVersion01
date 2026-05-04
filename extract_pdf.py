import PyPDF2
import sys

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            text += page.extract_text() + '\n'
        return text

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)
    lines = text.split('\n')
    
    # Simple context matching for Gateway and Nginx
    keywords = ["gateway", "nginx", "api"]
    results = []
    
    # Keep track of recent lines to provide context
    context_size = 5
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if "gateway" in line_lower or "nginx" in line_lower:
            start = max(0, i - context_size)
            end = min(len(lines), i + context_size + 1)
            results.append(f"--- Match at line {i} ---")
            results.append('\n'.join(lines[start:end]))
            
    # Also write out the full text to a file so we can view it
    with open('pdf_content.txt', 'w', encoding='utf-8') as out:
        out.write(text)
        
    print(f"Extracted {len(text)} characters. Full text saved to pdf_content.txt")
    
    # Print out matches
    print("\nMatches for Gateway / Nginx:")
    for r in results:
        print(r)
