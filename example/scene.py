
import numpy as np
import sys
import pathlib
sys.path.insert(0, '..')
import animation_exporter

def addHeader(rootnode):
    '''
    Header, with components to solve the collision between the objects in the scene (will be added to the given node)
    '''
    rootnode.addObject('FreeMotionAnimationLoop')
    rootnode.addObject('ProjectedGaussSeidelConstraintSolver', maxIterations=1000, tolerance=1e-8) # Solve the constraints (here the contacts)
    rootnode.addObject('CollisionPipeline')
    rootnode.addObject('BruteForceBroadPhase')
    rootnode.addObject('BVHNarrowPhase')
    rootnode.addObject('LocalMinDistance', alarmDistance="50", contactDistance="1") # Detection method (here proximity distance)
    rootnode.addObject('RuleBasedContactManager', response="FrictionContactConstraint", responseParams="mu=0.1") # We define the method for the contact response (here friction with a coefficient = 0.1)

    rootnode.gravity = [0, -9810, 0]
    rootnode.dt = 0.007 # time step

def addSettings(root):
    root.addObject('RequiredPlugin', name='BeamAdapter') # Needed to use components [AdaptiveBeamForceFieldAndMass,BeamInterpolation]
    root.addObject('RequiredPlugin', name='Sofa.Component.AnimationLoop') # Needed to use components [FreeMotionAnimationLoop]
    root.addObject('RequiredPlugin', name='Sofa.Component.Collision.Detection.Algorithm') # Needed to use components [BVHNarrowPhase,BruteForceBroadPhase,CollisionPipeline]
    root.addObject('RequiredPlugin', name='Sofa.Component.Collision.Detection.Intersection') # Needed to use components [LocalMinDistance]
    root.addObject('RequiredPlugin', name='Sofa.Component.Collision.Geometry') # Needed to use components [LineCollisionModel,PointCollisionModel,TriangleCollisionModel]
    root.addObject('RequiredPlugin', name='Sofa.Component.Collision.Response.Contact') # Needed to use components [RuleBasedContactManager]
    root.addObject('RequiredPlugin', name='Sofa.Component.Constraint.Lagrangian.Correction') # Needed to use components [GenericConstraintCorrection]
    root.addObject('RequiredPlugin', name='Sofa.Component.Constraint.Lagrangian.Solver') # Needed to use components [ProjectedGaussSeidelConstraintSolver]
    root.addObject('RequiredPlugin', name='Sofa.Component.Constraint.Projective') # Needed to use components [FixedProjectiveConstraint]
    root.addObject('RequiredPlugin', name='Sofa.Component.Engine.Generate') # Needed to use components [GenerateRigidMass]
    root.addObject('RequiredPlugin', name='Sofa.Component.IO.Mesh') # Needed to use components [MeshExporter,MeshOBJLoader]
    root.addObject('RequiredPlugin', name='Sofa.Component.LinearSolver.Direct') # Needed to use components [SparseLDLSolver]
    root.addObject('RequiredPlugin', name='Sofa.Component.Mapping.Linear') # Needed to use components [BarycentricMapping,SkinningMapping]
    root.addObject('RequiredPlugin', name='Sofa.Component.Mapping.NonLinear') # Needed to use components [RigidMapping]
    root.addObject('RequiredPlugin', name='Sofa.Component.Mass') # Needed to use components [UniformMass]
    root.addObject('RequiredPlugin', name='Sofa.Component.ODESolver.Backward') # Needed to use components [EulerImplicitSolver]
    root.addObject('RequiredPlugin', name='Sofa.Component.SolidMechanics.FEM.Elastic') # Needed to use components [HexahedronFEMForceField]
    root.addObject('RequiredPlugin', name='Sofa.Component.StateContainer') # Needed to use components [MechanicalObject]
    root.addObject('RequiredPlugin', name='Sofa.Component.Topology.Container.Constant') # Needed to use components [MeshTopology]
    root.addObject('RequiredPlugin', name='Sofa.Component.Topology.Container.Grid') # Needed to use components [RegularGridTopology]
    root.addObject('RequiredPlugin', name='Sofa.GL.Component.Rendering3D') # Needed to use components [OglModel]

def createScene(rootnode):
    '''
    Simulation scene
    '''
    addHeader(rootnode)
    settings = rootnode.addChild('Settings')
    addSettings(settings)
    
    beamOrigin = np.array([-100, 40, 0])

    # Meshes
    meshLoaders = rootnode.addChild("MeshLoaders")
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderSaladBowl', filename="meshes/saladBowl.obj", scale3d=[200, 200, 70], translation=[35,-25,0], rotation=[-90,0,0])
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderD20Coarse', filename="meshes/icosahedronCoarse.obj", scale=20)
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderD20Fine', filename="meshes/icosahedronFine.obj", scale=20)
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderBeam', filename="meshes/cylinder.obj", triangulate=True, scale=10, rotation=[0, 0, -90], translation=beamOrigin)

    # Environment (a node for the static objects, the objects that do not move)
    environment = rootnode.addChild("Environment")

    ## Salad Bowl
    bowl = environment.addChild("SaladBowl")
    bowl.addObject('MeshTopology', src=meshLoaders.meshLoaderSaladBowl.linkpath)
    bowl.addObject('MechanicalObject')
    bowl.addObject('TriangleCollisionModel')
    bowl.addObject('PointCollisionModel')
    bowl.addObject('LineCollisionModel')

    bowlVisual = bowl.addChild("Visual")
    bowlVisual.addObject('OglModel', src=meshLoaders.meshLoaderSaladBowl.linkpath, color=[0.5, 0.3, 0.2, 1.0])

    import pathlib
    meshPath = pathlib.Path("meshes/saladBowl").resolve()
    # We want to add to the Blender scene the bowl from a obj file with some transformations
    animation_exporter.addExportComponentsToNode(name=bowl.name.value, # the name of the object set in the Blender scene
                                                 mechaNode=bowl, # for static objects, any node will work
                                                 meshFilename=meshPath, # the absolute path where the mesh is located on the computer 
                                                 scale=meshLoaders.meshLoaderSaladBowl.scale3d.value, # we apply yhe same transformation than to the meshLoader
                                                 translation=meshLoaders.meshLoaderSaladBowl.translation.value,
                                                 rotation=meshLoaders.meshLoaderSaladBowl.rotation.value,
                                                 objectType="static" # the bowl doesn't move in the scene
                                                 )

    # Simulation
    simulation = rootnode.addChild('Simulation')
    simulation.addObject('EulerImplicitSolver')
    simulation.addObject('SparseLDLSolver', template="CompressedRowSparseMatrixMat3x3d")
    simulation.addObject('GenericConstraintCorrection')

    ## Deformable Beam    
    beam = simulation.addChild("Beam")
    beam.addObject("MeshTopology", position=[beamOrigin, beamOrigin+[50,0,0], beamOrigin+[100,0,0]], edges=[[0,1], [1,2]])
    beam.addObject("MechanicalObject", template="Rigid3", showObject=True, showObjectScale=5)
    beam.addObject('BeamInterpolation', 
                    crossSectionShape="circular",
                    defaultYoungModulus=1e4,  
                    defaultPoissonRatio=0.45,
                    radius=10)
    beam.addObject('AdaptiveBeamForceFieldAndMass', computeMass=True, massDensity=1e-8)
    beam.addObject("FixedProjectiveConstraint", indices=[0])  # Fix one end of the beam

    beamVisual = beam.addChild("Visual")
    beamVisual.addObject("OglModel", src=meshLoaders.meshLoaderBeam.linkpath, color=[0.8, 0.3, 0.3, 1.0])
    beamVisual.addObject("SkinningMapping")

    beamCollision = beam.addChild('Collision')
    beamCollision.addObject('MeshTopology', src=meshLoaders.meshLoaderBeam.linkpath)
    beamCollision.addObject('MechanicalObject')
    beamCollision.addObject('TriangleCollisionModel')
    beamCollision.addObject('PointCollisionModel')
    beamCollision.addObject('LineCollisionModel')
    beamCollision.addObject("SkinningMapping")

    # We want to add to the Blender scene the deformable beam
    # Since we want the positions of all the mesh vertices and not the beam, we passs the beamCollision as the `mechaNode` since it contains the mechanicalObject needed
    animation_exporter.addExportComponentsToNode(name=beam.name.value, # the name of the object set in the Blender scene
                                                 mechaNode=beamCollision, # the beamCollision node is the one holding the moving vertices
                                                 indices=list(range(len(meshLoaders.meshLoaderBeam.position.value))), # indices are all the indices of the meshLoaderBeam because it is the only one holding the all the indices at construction time
                                                 topologyNode=beamCollision,  # the node containing the topology we want to export as a mesh (.obj file). It will contain the MeshExporter component.
                                                 vertices=beamCollision.MeshTopology.position.value, # the vertices we will put into the .obj file. Note that the MeshTopology 
                                                 objectType="deformable", # the beam is a mesh that deforms
                                                 template="Vec3" # the template of the mechanical object governing the animation i.e. `mechaNode`
                                                 )
    
    ###  We could have used the cylinder.obj file instead of exporting the beamCollision mesh.
    # meshPath = pathlib.Path("meshes/cylinder").resolve()
    # animation_exporter.addExportComponentsToNode(name=beam.name.value, # the name of the object set in the Blender scen
    #                                              mechaNode=beamCollision, # the collision node is the one holding the vertices that will move
    #                                              indices=list(range(len(meshLoaders.meshLoaderBeam.position.value))), # indices are all the indices of the meshLoaderBeam because it is the only one holding the all the indices at construction time
    #                                              meshFilename=meshPath, # the absolute path where the mesh is located on the computer 
    #                                              objectType="deformable", # the beam is a mesh that deforms
    #                                              template="Vec3" # the template of the mechanical object governing the animation i.e. `mechaNode`
    ####                                           )

    ## Rigid D20
    d20 = simulation.addChild("d20")

    # We compute the inertia matrix of the dice
    massMatrix = rootnode.addChild('MassMatrix')
    massMatrix.addObject('GenerateRigidMass', src=meshLoaders.meshLoaderD20Coarse.linkpath, density=1e-6)

    d20.addObject("MechanicalObject", template="Rigid3", position=[[0,100,0,0,0,0,1]])
    d20.addObject('UniformMass', vertexMass=massMatrix.GenerateRigidMass.rigidMass.linkpath)

    d20Visual = d20.addChild('Visual')
    d20Visual.addObject('OglModel', src=meshLoaders.meshLoaderD20Coarse.linkpath, color=[0.3, 0.3, 0.5, 1.0])
    d20Visual.addObject('RigidMapping')

    d20Collision = d20.addChild('Collision')
    d20Collision.addObject('MeshTopology', src=meshLoaders.meshLoaderD20Coarse.linkpath)
    d20Collision.addObject('MechanicalObject')
    d20Collision.addObject('TriangleCollisionModel')
    d20Collision.addObject('PointCollisionModel')
    d20Collision.addObject('LineCollisionModel')
    d20Collision.addObject('RigidMapping')

    # We want to add to the Blender scene the rigid d20
    # since the d20 node is a Rigid, the mechanical object only has one point so we need to export the mesh frm another node
    # We provide `topologyNode` and `vertices` to export into a mesh obj file. We could have given the icosahedron.obj file instead but here is to give an example
    animation_exporter.addExportComponentsToNode(name=d20.name.value, # the name of the object set in the Blender scen
                                                 mechaNode=d20,  # the node holding the mechanichal state of the rigid
                                                 indices=[0], # a rigid mechanichal state only has one vertex
                                                 topologyNode=d20Collision, # the node containing the topology we want to export as a mesh (.obj file). It will contain the MeshExporter component
                                                 vertices=meshLoaders.meshLoaderD20Coarse.position.value, # the vertices we will put into the .obj file
                                                 objectType="rigid", # it is a rigid moving object
                                                 template="Rigid3" # the template of the mechanical object governing the animation i.e. `mechaNode`
                                                 )
    
    ## Jelly D20
    jellyD20 = simulation.addChild("JellyD20")

    jellyD20.addObject("RegularGridTopology", n=[6, 6, 6], min=[-20, -20, -20], max=[20, 20, 20])
    jellyD20.addObject("MechanicalObject")
    jellyD20.addObject('UniformMass', totalMass=0.05)
    jellyD20.addObject("HexahedronFEMForceField", youngModulus=5, poissonRatio=0.49)

    jellyD20Visual = jellyD20.addChild('Visual')
    jellyD20Visual.addObject('OglModel', src=meshLoaders.meshLoaderD20Fine.linkpath, color=[0.8, 0.3, 0.5, 1.0])
    jellyD20Visual.addObject('BarycentricMapping')

    # Create a node containing the Mechanical object and topology we want to export. Because the die is deformable, we need to export the fine mesh
    jellyD20BlenderVisual = jellyD20.addChild('BlenderVisual')
    jellyD20BlenderVisual.addObject('MeshTopology', src=meshLoaders.meshLoaderD20Fine.linkpath)
    jellyD20BlenderVisual.addObject('MechanicalObject')
    jellyD20BlenderVisual.addObject('BarycentricMapping')

    jellyD20Collision = jellyD20.addChild('Collision')
    jellyD20Collision.addObject('MeshTopology', src=meshLoaders.meshLoaderD20Coarse.linkpath)
    jellyD20Collision.addObject('MechanicalObject')
    jellyD20Collision.addObject('TriangleCollisionModel')
    jellyD20Collision.addObject('PointCollisionModel')
    jellyD20Collision.addObject('LineCollisionModel')
    jellyD20Collision.addObject('BarycentricMapping')

    meshPath = pathlib.Path("meshes/icosahedronFine").resolve()
    # We want to add to the Blender scene the a deformable d20
    # because we give the obj mesh file, we don't need to provide `topologyNode` and `vertices`.
    animation_exporter.addExportComponentsToNode(
                                                 name=jellyD20.name.value, # the name of the object set in the Blender scen
                                                 mechaNode=jellyD20BlenderVisual, # the node holding the points we want to export
                                                 objectType="deformable", # the points of the mesh will deform
                                                 template="Vec3", # the template of the mechanical object governing the animation i.e. `mechaNode`
                                                 indices=list(range(len(meshLoaders.meshLoaderD20Fine.position.value))), # the indices of the points we want to export. We use the meshLoader because it's the only node that has the positions at scene construction
                                                 meshFilename=meshPath # the absolute path where the mesh is located on the computer 
                                                 ) 

    animation_exporter.exportAnimationConfig("scene_config.toml") # create the toml file