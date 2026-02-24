from openstaadpy import os_analytical
import plotly.graph_objects as go

staad = os_analytical.connect()

nodes = staad.Geometry.GetNodeList()
members = staad.Geometry.GetBeamList()

fig = go.Figure()

for member in members:
    node1, node2 = staad.Geometry.GetMemberIncidence(member)
    
    x = []
    y = []
    z = []
    
    for node in [node1, node2]:
        coord = staad.Geometry.GetNodeCoordinates(node)
        x.append(coord[0])
        y.append(coord[1])
        z.append(coord[2])
    
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='lines'))

fig.show()