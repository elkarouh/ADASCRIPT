#! /usr/bin/env python3
from dataclasses import dataclass
from collections import namedtuple
from pathlib import Path
LS_COMMAND="Clsview"
####################################################################################
prefix,suffix='\x1b[','m'
class Style:
    def __init__(self, code):
        self.on, self.off = f"{prefix}{code}{suffix}", f"{prefix}0{suffix}"
    def __call__(self, *args):
        return f"{''.join([f'{self.on}{arg}' for arg in args])}{self.off}"
    def __ror__(self,other):
        return self(other)
#Style=type('Style',(),{'__init__':lambda s,c:setattr(s,'on',"\x1b["+f"{c}m") or setattr(s,'off',"\x1b[0m"),'__call__':lambda s,*a: "%s%s"%(''.join(["%s%s"% (s.on, arg) for arg in a]),s.off),'__ror__':lambda s,o:s(o)})
reset,bold,dim,_,underscore,blink,_,inverted = [Style(0+i) for i in range(8)]
black,      red,   green,   yellow,   blue,   magenta,   cyan,   white = [Style(30+i) for i in range(8)]
bg_black,bg_red,bg_green,bg_yellow,bg_blue,bg_magenta,bg_cyan,bg_white,_,bg_default = [Style(40+i) for i in range(10)]
################################################################################################
def align(length):
  def decorator(fun):
    def wrapper(string):
      return f"{fun(string):<{length}}"
    return wrapper
  return decorator
#####################################################################################
@align(64)
def colored_viewname (view_name):
  login_name,view=view_name.split('.')
  if view.startswith("I2_"):
    return f"{login_name}.{view |inverted| bold | blue | bg_white}"
  else:
    return f"{login_name}.{view |dim | bold | black | bg_white }"
@align(98)
def colored_baseline(baseline):
  parts=baseline.split('.')
  if parts[5:]:
      return f"{parts[0] | bold | yellow | bg_black}.{parts[1]}.{parts[2]}.{parts[3]| bold| yellow}.{parts[4]}.{parts[5] | bold | bg_blue | white}"
  else:
      return f"{parts[0] | bold | yellow | bg_black}.{parts[1]}.{parts[2]}.{parts[3]| bold| yellow}.{parts[4]| bold | bg_blue | white}"

@align(40)
def colored_env_id(env_id):
  parts=env_id.split('.')
  if parts[1]=="OP":
    return f"{parts[0]}.{parts[1] | bold | yellow | bg_black}.{parts[2]}"
  else:
    return f"{parts[0]}.{parts[1] | bold | blue | bg_white}.{parts[2]}"
@align(36)
def colored_status(state):
  if state=="OPS-BUG":
    return state | bold | blink | black | bg_white
  elif state=="BUSY":
    return state | bold | black | bg_yellow
  else:
    return state | bold | yellow | bg_green
@align(35)
def colored_comment(comment):
    return (comment[0].strip() if comment else "") | bold | black | bg_white

#####################################################################################
#import fileinput,sys
#for line in fileinput.input(sys.argv[1],inplace=True):
#	line=line.replace(sys.argv[2],sys.argv[3])
#	print(line,end="")
@dataclass
class Cls_View_Line:
    view: str
    baseline: str
    env_id: str
    state: str
    comment: str
# Cls_View_Line=namedtuple('Cls_View_Line',['view','baseline','env_id','state','comment'])
#####################################################################################
import subprocess, os
def run_command(cmd_lst): # run a external program and retrieve output line by line
    p=subprocess.Popen(cmd_lst,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')
def get_parsed_text(filename) -> str:
    return "".join(line.decode('utf8') for line in run_command(f'difft --dump-ts {filename}'.split()))
def get_lines() -> str:
    return [line.decode('utf8') for line in run_command(f"{LS_COMMAND} -user {os.environ['USER']}".split())]
######################################################################################
lines=get_lines()
print("-"*100)
title_elements = ('View', 'Based On', 'ENV_ID', 'State','COMMENT')
print(f"{title_elements[0]:<31}{title_elements[1]:<30}{title_elements[2]:<15}{title_elements[3]:<11}{title_elements[4]}")
print("-"*100)
view_lines=[]
for line in lines[3:]:
  try:
    view_name, baseline, env_id, built, status, *x= line.split()
  except:
    print(f"unable to parse {line=}")
    continue
  comment_file= Path.home() / "cm" / view_name / "README.txt"
  state,comment="",""
  if not comment_file.exists():
    parts = list(comment_file.parts)
    if view_name.endswith(('_t','_i')):
      parts[-2] =parts[-2].replace('_t','_e').replace('_i','_e')
    else:
      parts[-2] =parts[-2].replace('_e','_t')
    comment_file = Path(*parts)
  if comment_file.exists():
    with open(comment_file, 'r') as file:
      comment_line = file.readline().rstrip() # first line is the state comment
      state, *comment=comment_line.split(' ',1)
  if status!='---':
    state=status
  if view_name.endswith("build_eld_only_t"):
    continue
  view_lines.append(Cls_View_Line(view=view_name,
                                  baseline=baseline,
                                  env_id=env_id,
                                  state=state,
                                  comment=comment))

STATES = ('ACTIVE', 'READY', 'OPS-BUG', 'DONE', 'BLOCKED', 'ON-HOLD', 'IDLE', 'BACKGROUND','INTEGRATED','MERGED','REJECTED')
sep_line1_written=False
sep_line2_written=False
sep_line3_written=False
# sort on state then on view name
previous_state=None
for R in sorted(view_lines, key=lambda r: (STATES.index(r.state) if r.state in STATES else len(STATES),r.view)):
  if previous_state is not None and R.state != previous_state:
    print('-'*120)
  colored_line=f"{colored_viewname(R.view)} {colored_baseline(R.baseline)} {colored_env_id(R.env_id)} {colored_status(R.state)}"
  if R.state!='MERGED':
    colored_line+=f" {colored_comment(R.comment)}"
  print(colored_line)
  previous_state=R.state
