# bsp_tool-examples
 Example scripts for snake-biscuits/bsp_tool
 
Many of these scripts are old experiments, and as a result are not well maintained  

### Converting .bsp to .obj
  Drag the desired .bsp file(s) over `obj_files/obj_model_from_bsp.py`  
  An .obj file will appear next to the .bsp, wherever you dragged it from
  
### Rendering .bsp files in 3D
  `visualise/render_bsp.py` requires some external libraries  
  Install them by running `$ pip install -r requirements.txt` in the top level folder  
  `visualise/render_bsp.py` is intended to be run from an IDE  
  The .bsp you want to see must be entered into the script manually
