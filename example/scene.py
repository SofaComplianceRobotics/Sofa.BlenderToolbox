import random
from splib3.numerics import Quat
from math import pi
import Sofa.Core 
import numpy as np
import sys
sys.path.insert(0, '..')
import animation_exporter

def createScene(rootnode):
    rootnode.addObject('FreeMotionAnimationLoop')
    rootnode.addObject('ProjectedGaussSeidelConstraintSolver', maxIterations=500, tolerance=1e-6)
    rootnode.addObject('CollisionPipeline')
    rootnode.addObject('BruteForceBroadPhase')
    rootnode.addObject('BVHNarrowPhase')
    rootnode.addObject('LocalMinDistance', alarmDistance="20", contactDistance="5")
    rootnode.addObject('RuleBasedContactManager', response="FrictionContactConstraint", responseParams="mu=0.3")

    rootnode.gravity = [0, -9810, 0]
    rootnode.dt = 0.0008
    
    beamOrigin = np.array([-1000, 400, 0])

    # Meshes
    meshLoaders = rootnode.addChild("MeshLoaders")
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderTray', filename="meshes/saladBowl.obj", scale3d=[2000, 2000, 700], translation=[350,-250,0], rotation=[-90,0,0])
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderD20', filename="meshes/icosahedron.obj", scale=100)
    meshLoaders.addObject('MeshOBJLoader', name='meshLoaderBeam', filename="meshes/cylinder.obj", scale=100, rotation=[0, 0, -90], translation=beamOrigin)

    # Environment (does not move)
    environment = rootnode.addChild("Environment")

    ## Tray
    tray = environment.addChild("Tray")
    tray.addObject('OglModel', src=meshLoaders.meshLoaderTray.linkpath, color=[0.5, 0.3, 0.2, 1.0])
    tray.addObject('MeshTopology', src=meshLoaders.meshLoaderTray.linkpath)
    tray.addObject('MechanicalObject')
    tray.addObject('TriangleCollisionModel')
    tray.addObject('PointCollisionModel')
    tray.addObject('LineCollisionModel')
    # Add components to export the tray in a blender scene
    # The tray is a static object since it is not moving in the simulation. 
    # Here we pass the vertices so a mesh obj file will be generated from these vertices. We could have directly pass the path to the saladBowl.obj
    # The template does not matter for a static object
    # Since the tray is static, indices does not matter
    animation_exporter.addExportComponentsToNode(name=tray.name.value, 
                              mechaNode=tray,
                              indices=[], # indices don't matter for static
                              topologyNode=tray, 
                              vertices=tray.OglModel.position.value,
                              objectType="static")

    # Simulation
    simulation = rootnode.addChild('Simulation')
    simulation.addObject('EulerImplicitSolver')
    simulation.addObject('SparseLDLSolver', template="CompressedRowSparseMatrixMat3x3d")
    simulation.addObject('GenericConstraintCorrection')

    ## Beam    
    beam = simulation.addChild("Beam")
    beam.addObject("MeshTopology", position=[beamOrigin, beamOrigin+[500,0,0], beamOrigin+[1000,0,0]], edges=[[0,1], [1,2]])
    beam.addObject("MechanicalObject", template="Rigid3", showObject=True, showObjectScale=5)
    beam.addObject('BeamInterpolation', 
                    crossSectionShape="circular",
                    defaultYoungModulus=1e4,  
                    defaultPoissonRatio=0.45,
                    radius=100)
    beam.addObject('AdaptiveBeamForceFieldAndMass', computeMass=True, massDensity=1e-6)
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

    # Add components to export the Beam animation in a blender scene
    # Since we want the positions of all the mesh and not the beam, we passs the beamCollision as the mechaNode
    # We pass vertices from the visual model so a mesh will be generated from them
    # Since it is a deformable, the template is Vec3
    # indices are all the indices of the mechanical object
    animation_exporter.addExportComponentsToNode(name=beam.name.value, 
                              mechaNode=beamCollision, 
                              indices=list(range(len(meshLoaders.meshLoaderBeam.position.value))),
                              topologyNode=beamCollision, 
                              vertices=beamVisual.OglModel.position.value,
                              objectType="deformable",
                              template="Vec3"
                              )

    ## D20
    d20 = simulation.addChild("d20")

    position=[[0,1000,0,0,0,0,1]]
    d20.addObject("MechanicalObject", template="Rigid3", position=position)
    d20.addObject('UniformMass', totalMass=0.5)

    d20Visual = d20.addChild('Visual')
    d20Visual.addObject('OglModel', src=meshLoaders.meshLoaderD20.linkpath, color=[0.3, 0.3, 0.5, 1.0])
    d20Visual.addObject('RigidMapping')

    d20Collision = d20.addChild('Collision')
    d20Collision.addObject('MeshTopology', src=meshLoaders.meshLoaderD20.linkpath)
    d20Collision.addObject('MechanicalObject')
    d20Collision.addObject('TriangleCollisionModel')
    d20Collision.addObject('PointCollisionModel')
    d20Collision.addObject('LineCollisionModel')
    d20Collision.addObject('RigidMapping')

    import pathlib
    meshPath = pathlib.Path("meshes/icosahedron").resolve()
    print(meshPath)
    animation_exporter.addExportComponentsToNode(
        name=d20.name.value, 
        mechaNode=d20,
        vertices=meshLoaders.meshLoaderD20.position.value,
        objectType="rigid", 
        template="Rigid3", 
        indices=[0], 
        scale=meshLoaders.meshLoaderD20.scale3d.value, 
        meshFilename=meshPath)

    animation_exporter.exportAnimationConfig("scene_config.toml") # create the toml file