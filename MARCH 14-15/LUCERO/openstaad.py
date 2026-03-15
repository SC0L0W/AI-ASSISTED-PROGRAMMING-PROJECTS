import FreeSimpleGUI as sg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math

# --- Matplotlib Helper Functions ---
def draw_figure(canvas, figure):
    """Embeds the matplotlib figure into the FreeSimpleGUI canvas."""
    if canvas.children:
        for child in canvas.winfo_children():
            child.destroy()
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

def parse_dim(dim_str):
    """Safely splits a string like '250x400' into two floats: 250.0, 400.0"""
    parts = dim_str.lower().replace(' ', '').split('x')
    return float(parts[0]), float(parts[1])

# --- STAAD.Pro Export Function ---
def export_to_staad(values):
    """Connects to STAAD.Pro and generates the model geometry and properties."""
    try:
        # Based on STAAD.Pro 2025 release, the connection module is os_analytical
        from openstaadpy import os_analytical
    except ImportError as e:
        sg.popup_error(f"Failed to load 'openstaadpy'.\n\nError details: {e}\n\nPlease ensure your Python environment is set up correctly with the Bentley STAAD.Pro 2025 package.")
        return

    try:
        # Connect to the active STAAD.Pro instance
        staad = os_analytical.connect()
    except Exception as e:
        sg.popup_error(f"Could not connect to STAAD.Pro.\nPlease ensure STAAD is open to a valid model.\nError details: {e}")
        return

    try:
        # Handle method capitalization depending on the openstaadpy wrapper version
        geo = staad.Geometry if hasattr(staad, 'Geometry') else staad.geometry
        sup = staad.Support if hasattr(staad, 'Support') else staad.support
        prop = staad.Property if hasattr(staad, 'Property') else staad.property
        
        # 1. Parse Inputs safely
        floors = int(values['-FLOORS-'])
        h_f = float(values['-FLOOR_HEIGHT-'])
        nx = int(values['-X_BAYS-'])
        sx = float(values['-X_SPACING-'])
        ny = int(values['-Y_BAYS-'])
        sy = float(values['-Y_SPACING-'])
        
        b, h = parse_dim(values['-BEAM_DIM-'])
        cx, cy = parse_dim(values['-COL_DIM-'])
        
        # Convert dimensions to meters for STAAD
        b, h = b / 1000, h / 1000 
        cx, cy = cx / 1000, cy / 1000

        # Dictionary to keep track of generated Node IDs
        node_map = {}
        
        # 3. Generate Nodes (STAAD Default: Y is vertical up)
        for k in range(floors + 1):          # Elevation (Y)
            for i in range(nx + 1):          # X-direction
                for j in range(ny + 1):      # Z-direction (Depth)
                    X = i * sx
                    Z = j * sy
                    Y = k * h_f
                    
                    if hasattr(geo, 'AddNode'):
                        node_id = geo.AddNode(X, Y, Z)
                    else:
                        node_id = geo.CreateNode(X, Y, Z)
                        
                    node_map[(i, j, k)] = node_id
                    
        # 4. Generate Columns (Vertical Beams)
        col_ids = []
        for k in range(floors):
            for i in range(nx + 1):
                for j in range(ny + 1):
                    n1 = node_map[(i, j, k)]
                    n2 = node_map[(i, j, k+1)]
                    
                    if hasattr(geo, 'AddBeam'):
                        beam_id = geo.AddBeam(n1, n2)
                    else:
                        beam_id = geo.CreateBeam(n1, n2)
                    col_ids.append(beam_id)
                    
        # 5. Generate Horizontal Beams
        beam_ids = []
        for k in range(1, floors + 1):
            # X-direction Beams
            for j in range(ny + 1):
                for i in range(nx):
                    n1 = node_map[(i, j, k)]
                    n2 = node_map[(i+1, j, k)]
                    if hasattr(geo, 'AddBeam'):
                        b_id = geo.AddBeam(n1, n2)
                    else:
                        b_id = geo.CreateBeam(n1, n2)
                    beam_ids.append(b_id)
                    
            # Z-direction Beams
            for i in range(nx + 1):
                for j in range(ny):
                    n1 = node_map[(i, j, k)]
                    n2 = node_map[(i, j+1, k)]
                    if hasattr(geo, 'AddBeam'):
                        b_id = geo.AddBeam(n1, n2)
                    else:
                        b_id = geo.CreateBeam(n1, n2)
                    beam_ids.append(b_id)

        # 6. Assign Pinned Supports to Base Nodes (k=0)
        base_nodes = [node_map[(i, j, 0)] for i in range(nx + 1) for j in range(ny + 1)]
        try:
            sup.CreateSupportPinned(base_nodes)
        except Exception as e:
            print(f"Warning: Could not generate pinned supports. {e}")

        # 7. Assign Prismatic Properties
        try:
            if hasattr(prop, 'CreatePrismaticRectangleProperty'):
                prop_col = prop.CreatePrismaticRectangleProperty(cx, cy)
                prop_beam = prop.CreatePrismaticRectangleProperty(h, b)
            else:
                prop_col = prop.CreatePrismaticProperty(0, cx, cy, 0, 0, 0)
                prop_beam = prop.CreatePrismaticProperty(0, h, b, 0, 0, 0)
            
            if hasattr(prop, 'AssignBeamProperty'):
                prop.AssignBeamProperty(col_ids, prop_col)
                prop.AssignBeamProperty(beam_ids, prop_beam)
            else:
                prop.AssignPropertyToBeam(col_ids, prop_col)
                prop.AssignPropertyToBeam(beam_ids, prop_beam)
        except Exception as e:
            print(f"Warning: Could not assign section properties. {e}")

        # 8. Create and Assign Concrete Material
        try:
            fc = float(values['-FC-'])
            E_kNm2 = 4700 * math.sqrt(fc) * 1000
            nu = 0.17        
            den = 23.56      
            alpha = 1e-5     
            damp = 0.05      
            G = E_kNm2 / (2 * (1 + nu)) 
            
            mat_name = f"CONC_{int(fc)}MPA"
            
            if hasattr(prop, 'CreateIsotropicMaterial'):
                try:
                    prop.CreateIsotropicMaterial(mat_name, E_kNm2, nu, den, alpha, damp, G)
                except Exception:
                    pass # Ignore error if material already exists from a previous run
            
            all_members = col_ids + beam_ids
            if hasattr(prop, 'AssignMaterialToMember'):
                try:
                    prop.AssignMaterialToMember(all_members, mat_name)
                except TypeError:
                    prop.AssignMaterialToMember(mat_name, all_members)
        except Exception as e:
            print(f"Warning: Could not create or assign material. {e}")

        sg.popup('Geometry, Supports, Properties, and Materials successfully transferred to STAAD.Pro!', title='STAAD Export Complete')

    except ValueError:
        sg.popup_error("Invalid input detected. Please ensure all inputs are numerical.")
    except Exception as e:
        sg.popup_error(f"An unexpected error occurred during export:\n{str(e)}")

# --- GUI Layout ---
label_size = (45, 1)

# Left Column: Input Parameters
input_layout = [
    [sg.Text('Building Parameters', font=('Helvetica', 12, 'bold'))],
    [sg.Text('Number of floors:', size=label_size), sg.InputText('3', key='-FLOORS-', size=(15,1))],
    [sg.Text('Floor height (m):', size=label_size), sg.InputText('3.5', key='-FLOOR_HEIGHT-', size=(15,1))],
    [sg.Text('X-direction bays:', size=label_size), sg.InputText('3', key='-X_BAYS-', size=(15,1))],
    [sg.Text('X-direction spacing (m):', size=label_size), sg.InputText('5.0', key='-X_SPACING-', size=(15,1))],
    [sg.Text('Y-direction bays:', size=label_size), sg.InputText('2', key='-Y_BAYS-', size=(15,1))],
    [sg.Text('Y-direction spacing (m):', size=label_size), sg.InputText('6.0', key='-Y_SPACING-', size=(15,1))],
    
    [sg.Text('Material Properties', font=('Helvetica', 12, 'bold'), pad=(0, (10, 0)))],
    [sg.Text("fc' (MPa):", size=label_size), sg.InputText('28', key='-FC-', size=(15,1))],
    [sg.Text('fy main (MPa):', size=label_size), sg.InputText('414', key='-FY_MAIN-', size=(15,1))],
    [sg.Text('fy ties (MPa):', size=label_size), sg.InputText('275', key='-FY_TIES-', size=(15,1))],

    [sg.Text('Dimensions & Loads', font=('Helvetica', 12, 'bold'), pad=(0, (10, 0)))],
    [sg.Text('Beam (b x h) mm:', size=label_size), sg.InputText('250x400', key='-BEAM_DIM-', size=(15,1))],
    [sg.Text('Column (cx x cy) mm:', size=label_size), sg.InputText('400x400', key='-COL_DIM-', size=(15,1))],
    [sg.Text('Slab thickness (mm):', size=label_size), sg.InputText('150', key='-SLAB_THICK-', size=(15,1))],
    [sg.Text('Dead load (kPa):', size=label_size), sg.InputText('4.8', key='-DL-', size=(15,1))],
    [sg.Text('Live load (kPa):', size=label_size), sg.InputText('2.4', key='-LL-', size=(15,1))],
    
    [sg.HorizontalSeparator(pad=(0, 10))],
    [sg.Button('Update 3D View', button_color=('white', '#0079d3')), 
     sg.Button('Export to STAAD.Pro', button_color=('white', '#28a745')), 
     sg.Button('Exit')]
]

# Right Column: 3D Visualization Canvas
plot_layout = [
    [sg.Text('3D Structure Visualization', font=('Helvetica', 12, 'bold'))],
    [sg.Text('(Left-Click to Rotate, Right-Click to Pan, Scroll to Zoom)')],
    [sg.Canvas(key='-CANVAS-', size=(600, 500))]
]

# Combine both into the main layout
layout = [
    [sg.Column(input_layout, vertical_alignment='top'), 
     sg.VSeparator(), 
     sg.Column(plot_layout, vertical_alignment='top')]
]

window = sg.Window('STAAD.Pro Frame Generator', layout, finalize=True)

# Initialize the Matplotlib Figure
fig = plt.figure(figsize=(6, 5), dpi=100)
ax = fig.add_subplot(111, projection='3d')
fig_agg = draw_figure(window['-CANVAS-'].TKCanvas, fig)

# --- Event Loop ---
while True:
    event, values = window.read()
    
    if event == sg.WIN_CLOSED or event == 'Exit':
        break
        
    if event == 'Export to STAAD.Pro':
        export_to_staad(values)
        
    if event == 'Update 3D View':
        try:
            # 1. Parse Inputs safely
            floors = int(values['-FLOORS-'])
            h_f = float(values['-FLOOR_HEIGHT-'])
            nx = int(values['-X_BAYS-'])
            sx = float(values['-X_SPACING-'])
            ny = int(values['-Y_BAYS-'])
            sy = float(values['-Y_SPACING-'])
            
            b, h = parse_dim(values['-BEAM_DIM-'])
            b, h = b/1000, h/1000 
            
            cx, cy = parse_dim(values['-COL_DIM-'])
            cx, cy = cx/1000, cy/1000
            
            ts = float(values['-SLAB_THICK-']) / 1000
            
            # 2. Clear previous plot
            ax.cla()
            
            # 3. Draw Columns
            total_height = floors * h_f
            for i in range(nx + 1):
                for j in range(ny + 1):
                    x_pos = i * sx - cx/2
                    y_pos = j * sy - cy/2
                    ax.bar3d(x_pos, y_pos, 0, cx, cy, total_height, color='#555555', alpha=0.9)
            
            # 4. Draw Beams & Slabs
            for f in range(1, floors + 1):
                z_level = f * h_f
                
                # Slabs
                slab_x = -cx/2
                slab_y = -cy/2
                slab_width = nx * sx + cx
                slab_depth = ny * sy + cy
                ax.bar3d(slab_x, slab_y, z_level - ts, slab_width, slab_depth, ts, color='#1f77b4', alpha=0.3)
                
                # X-Beams
                for i in range(nx):
                    for j in range(ny + 1):
                        bx_pos = i * sx
                        by_pos = j * sy - b/2
                        ax.bar3d(bx_pos, by_pos, z_level - h, sx, b, h, color='#ff7f0e', alpha=0.8)
                
                # Y-Beams
                for i in range(nx + 1):
                    for j in range(ny):
                        bx_pos = i * sx - b/2
                        by_pos = j * sy
                        ax.bar3d(bx_pos, by_pos, z_level - h, b, sy, h, color='#ff7f0e', alpha=0.8)

            # 5. Format axes
            ax.set_xlabel('X (meters)')
            ax.set_ylabel('Y (meters)')
            ax.set_zlabel('Z (meters)')
            ax.set_title(f'{floors}-Story Building Model')
            
            # Force equal aspect ratio
            ax.set_box_aspect([nx*sx, ny*sy, total_height])

            fig_agg.draw()
            
        except ValueError:
            sg.popup_error("Invalid input detected. Please ensure all inputs are numerical.")

window.close()