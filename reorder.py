import re

file_path = 'client/src/components/Dashboard.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

b_radar = re.search(r'(        \{\/\* 1\. Dimension Balance Radar Chart \*\/\}.*?        </div>\n)', content, re.DOTALL).group(1)
b_pillar = re.search(r'(        \{\/\* Widget 1: Pillar Comparison Bar Chart \*\/\}.*?        </div>\n)', content, re.DOTALL).group(1)
b_donut = re.search(r'(        <div className="glass-panel card-contribution-donut".*?        </div>\n)', content, re.DOTALL).group(1)
b_pressure = re.search(r'(        \{\/\* Widget 3: Pressure Index \(Packed Circle Redesign\) \*\/\}.*?        </div>\n)', content, re.DOTALL).group(1)
b_temp = re.search(r'(        \{\/\* Widget 4: Temperature Stress Index \*\/\}.*?        </div>\n)', content, re.DOTALL).group(1)
b_stacked = re.search(r'(        \{\/\* Widget 5: Concern Distribution Stacked Chart \*\/\}.*?        </div>\n)', content, re.DOTALL).group(1)

start_marker = r'        \{\/\* 1\. Dimension Balance Radar Chart \*\/\}'
end_marker = r'        \{\/\* Detailed Metrics Grid \*\/\}'

parts = re.split(rf'({start_marker}.*?)(?={end_marker})', content, flags=re.DOTALL)
if len(parts) == 3:
    new_content = parts[0] + '\n' + b_donut + '\n' + b_radar + '\n' + b_pressure + '\n' + b_stacked + '\n' + b_temp + '\n' + b_pillar + '\n\n' + parts[2]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Successfully reordered graphs!')
else:
    print('Failed to split content correctly.', len(parts))
