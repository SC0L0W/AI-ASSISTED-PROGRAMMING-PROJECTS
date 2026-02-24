from openstaad import Geometry, Root

geometry = Geometry()
root = Root()

# Function that returns a list
beam_list = geometry.GetBeamList()

# Function that retuns a string
file_name = root.GetSTAADFile()

# Function that recibe an argument
beam_number = 10 
beam_nodes = geometry.GetMemberIncidence(beam_number)


print(beam_list)
print(file_name)
print(beam_nodes)