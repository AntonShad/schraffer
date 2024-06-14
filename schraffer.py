#GPLv2


"""
  This script is a modified version of the original shaffer.py script. 
  www.github.com/hacxman/schraffer/blob/master/schraffer. The original script was written in python 2 and has been modified to work with python 3.
"""



import png
import os
import sys
import json
import datetime
try:
  from src.config import Config

except ModuleNotFoundError:
  from config import Config


gcodeoutput = ""

def pr(*l):
  return " ".join(map(str, l)) + "\n"

def get_pixel(i, x, y, meta):
  x *= meta['planes']
  w = meta['size'][0]
  l = i[y]
  return l[x]

def get_rect(img, x, y, size, meta):
  r = []
  for i in range(x-size, x+size):
    for j in range(y-size, y+size):
      r.append(get_pixel(img, x, y, meta))
  return r

def get_rect_avg(img, x, y, size, meta):
  s = 0.0
  count = 0
  for i in range(x-size, x+size):
    for j in range(y-size, y+size):
      s += get_pixel(img, x, y, meta)
      count += 1
  if count == 0:
    return 0
  return s / count

def get_average(pixels):
  return float(sum(pixels))/len(pixels)

def image_to_gcode(filepath: str):
  return main(filepath=filepath)


def image_to_gcode_data(bytes: bytes):
  return main(bytes=bytes)


def main(filepath: str = None, bytes: bytes = None):
  _gcodeoutput = ""
  with open('settings.json') as fin:
    settings = json.load(fin)
    dpm = float(settings['inputDPI'])/25.4
    spotsize = float(settings['spotSize'])
    machinedpm = float(settings['machineDPI'])/25.4
    basic_speed = float(settings['basicSpeed'])
    oversampling = float(settings['oversampling'])
    focus_speed = float(settings['focusSpeed'])
    travel_speed = float(settings['travelSpeed'])
    focusedZ = float(settings['focusedZ'])
    travelZ = float(settings['travelZ'])
    endZ = float(settings['endZ'])
    passes = int(settings['passes'])
  dpm = Config.get_instance("./data/config.ini")['dpi'] / 25.4
  # header
  _gcodeoutput += pr('G90') # absolute pos
  _gcodeoutput += pr('G21') # units in mm
  _gcodeoutput += pr('G28') # go home
  _gcodeoutput += pr('G00 Z{} F9000'.format(travelZ)) # go to standby position
  if filepath:
    w, h, img, meta = png.Reader(filename=filepath).asDirect()
  elif bytes:
    w, h, img, meta = png.Reader(bytes=bytes).asDirect()
  img = list(img)
  wdpm, hdpm = w/dpm, h/dpm
  linescount = hdpm / spotsize
  rowscount = wdpm / spotsize
  spot_in_img = spotsize * dpm

  

  if passes > 1:
    travelZ += 0.05
    focusedZ += 0.05
  for pass_id in range(passes):

    pen_is_up = True
    alt = False
    _cnt = 0
    _speed = basic_speed * oversampling # 170 is basic speed, 3 is oversampling
    #l_x, l_y = (0,0)
    for lnum in range(int((linescount-1)*oversampling)):
      lnum /= float(oversampling)
      rows = range(int((rowscount-1)*oversampling))
      rows = reversed(rows) if alt else rows
      alt = not alt
      _cnt += 1
      if _cnt > 10:
        print('PASS:', 1+pass_id, '/', passes, "{:.2f}%".format(100*lnum/float(linescount)), '   \r', end='', file=sys.stderr)
        _cnt = 0
      for rnum in rows:
         rnum /= float(oversampling)
         avg = get_rect_avg(img, int(spot_in_img*rnum+spot_in_img),
                            int(spot_in_img*lnum+spot_in_img),
                            int(spot_in_img), meta)
         _x, _y = lnum*spot_in_img/dpm, rnum*spot_in_img/dpm
         if avg < 250:
           if pen_is_up:
             _gcodeoutput += pr('G00 X{} Y{} Z{} F{}'.format(_x, _y, travelZ, travel_speed))
             pen_is_up = False
             if focus_speed > 0:
               _gcodeoutput += pr('G00 X{} Y{} Z{} F{}'.format(_x, _y, focusedZ, focus_speed))
             _gcodeoutput += pr('G05 L1')
             #l_x, l_y = (_x, _y)
         else:
           if not pen_is_up:
             _gcodeoutput += pr('G01 X{} Y{} Z{} F{}'.format(_x, _y, focusedZ, _speed))
             if focus_speed > 0:
               _gcodeoutput += pr('G00 X{} Y{} Z{} F{}'.format(_x, _y, travelZ, focus_speed))
             _gcodeoutput += pr('G05 L0')
             pen_is_up = True
    print('PASS:', 1+pass_id, '/', passes, "{:.2f}%".format(100*lnum/float(linescount)), '   \r', end='', file=sys.stderr)
    travelZ -= 0.05
    focusedZ -= 0.05
  # footer
  _gcodeoutput += pr('G01 Z{} F9000'.format(endZ))
  timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
  with open(f'gcode testing/output_{timestamp}.gcode', 'w') as fout:
    fout.write(_gcodeoutput)
  return _gcodeoutput

if __name__ == "__main__":
  main()
