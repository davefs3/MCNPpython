# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 14:21:49 2019

@author: HPersson
"""
import numpy as np
from abc import ABC, abstractmethod


class Source(ABC):
    """
    This is the base class that all other sources inherits from it should
    never be instanciated. The derived classes should be instanciated and they
    should implement all the source specific methods.
    """
    def __init__(self, energy, counter, nps, max_lost_particles=10, well_source=False):
        self.energy = energy
        self.counter = counter
        self.nps = nps
        self.x, self.y, self.z = self._xyz()
        self.r, self.theta, self.phi = self._rtp()
        self.max_lost_particles = max_lost_particles
        self.well_source = well_source

    def position(self):
        """
        The position comment that is printed at the beginning of
        each MCNP input file

        Returns
        -------
        str
            The position comment for MCNP input files.

        """
        return f'{self.x:.15} {self.y:.15} {self.z:.15} {self.r:.15} {180.0 - np.rad2deg(self.theta):.15}'

    def source(self, detector, full_detector=True):
        """
        The SDEF cards for the source. It includes a directional bias
        variance reduction.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        text : List
            The SDEF cards for the source detector combination.

        """
        text = [f'SDEF   ERG= {self.energy/1000.0:.6f}\n',
                f'       POS= {self.x:.8} {self.y:.8} {self.z:.8}\n',
                f'{self._cell_card()}',
                f'{self._vec(detector, full_detector)}',
                f'{self._dir()}',
                f'{self._axs()}',
                f'{self._ext()}',
                f'{self._rad()}',
                f'       WGT={self.weight(detector, full_detector):.18f}\n',
                f'{self._s1(detector, full_detector)}',
                f'{self._s2()}',
                f'{self._s3()}'
                ]
        return text

    def weight(self, detector, full_detector=True):
        """
        The source particle weight that comes from the directional
        bias variance reduction.

        It calculates the angle between the direction vector and the vector from the source
        corners to the detector corners and picks the weight for the largest
        angle.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        weight : float
            The weight from the directional bias variance reduction algorithm.

        """
        # check that if the point is inside the end cap. If it is then set the
        # weight to 1.0 and emit particles isotropically. Should only be relevant
        # for well detector.
        radius = self.x**2 + self.y**2
        if radius < detector.dimensions['ec_rad']**2 and self.z > 0 and self.z < detector.dimensions['ec_len']:
            return 1.0

        detector_corners = detector.corners(full_detector)
        direction = self._direction(detector, full_detector)
        source_corners = self._source_corners()
        weight = 0.0
        for det_corner in detector_corners:
            for source_corner in source_corners:
                corner_to_corner = det_corner - source_corner
                cos_opening_angle = np.dot(corner_to_corner, direction) / np.linalg.norm(corner_to_corner) / np.linalg.norm(direction)
                temp_weight = (1 - cos_opening_angle)/2.0
                if temp_weight > weight:
                    weight = temp_weight

        return weight

    def _s1(self, detector, full_detector):
        """
        The directional source distribution for use in MCNP.
        It's based on the weight from the directional bias algorithm.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        str
            The directional source distribution for use in MCNP.

        """
        return f'SI1    {1.0 - 2*self.weight(detector, full_detector):.18f} 1\nSP1    0 1\n'

    def _cell_card(self):
        """
        The cell card for the source. Defaults to blank, override if
        needed for the source

        Returns
        -------
        str
            Empty string.

        """
        return ''

    def _vec(self, detector, full_detector):
        """
        The vec card for the MCNP source

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        str
            The vec card for the source

        """
        direction = self._direction(detector, full_detector)
        return f'       VEC= {direction[0]:.8} {direction[1]:.8} {direction[2]:.8}\n'

    def _dir(self):
        """
        The MCNP dir card for the source.

        Returns
        -------
        str
            The DIR card for the source.

        """
        return '       DIR= D1\n'

    def _rtp(self):
        """
        The polar coordinates of the source reference point.

        Returns
        -------
        r : float
            The r polar coordinate.
        theta : float
            The theta polar coordinate.
        phi : float
            The phi polar coordinate.

        """
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        theta = np.arccos(self.z/r)
        phi = np.arctan2(self.y, self.x)
        return r, theta, phi

    def _direction(self, detector, full_detector):
        """
        The direction from the source reference point to the center of
        the detector. It is used in MCNP for the DIR card.


        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        np.array
            The normalized direction vector.

        """
        center = detector.center(full_detector)
        x1 = center[0] - self.x
        y1 = center[1] - self.y
        z1 = center[2] - self.z
        return np.array([x1, y1, z1]) / np.sqrt(x1**2 + y1**2 + z1**2)

    def lost_card(self):
        """
        The lost card in MCNP.

        Returns
        -------
        str
            The lost card in MCNP.

        """
        if self.max_lost_particles == 10:
            return ''
        return f'LOST {self.max_lost_particles} {self.max_lost_particles}\n'

    @classmethod
    def low_energy(cls, energy):
        """
        Check if the energy is above the low energy validation limit.
        Override this method for sources with a different low energy limit.

        Parameters
        ----------
        energy : float
            The energy that is compared to the low energy limit.

        Returns
        -------
        bool
            True if energy < 35.

        """
        return energy < 35

    # The following method needs to be implemented by the classes inheriting
    # from this abstract base class

    @abstractmethod
    def cells(self, detector, electrontrack):
        pass

    @abstractmethod
    def cell_numbers(self):
        pass

    @abstractmethod
    def material_numbers(self):
        pass

    @abstractmethod
    def surfaces(self):
        pass

    @abstractmethod
    def max_radius(self):
        pass

    @abstractmethod
    def air_density(self):
        pass

    @abstractmethod
    def _xyz(self):
        pass

    @abstractmethod
    def _axs(self):
        pass

    @abstractmethod
    def _ext(self):
        pass

    @abstractmethod
    def _rad(self):
        pass

    @abstractmethod
    def _s2(self):
        pass

    @abstractmethod
    def _s3(self):
        pass

    @abstractmethod
    def _source_corners(self):
        pass


class XD(Source):
    def __init__(self, energy, counter, nps, arm_length, pivot, angle, source_radius=0.165, source_thickness=0.15,
                 front_surface_thickness=0.03, capsule_radius=0.5):
        self.angle = angle
        self.source_radius = source_radius
        self.source_thickness = source_thickness
        self.front_surface_thickness = front_surface_thickness
        self.capsule_radius = capsule_radius
        self.arm_length = arm_length
        self.pivot = pivot
        super().__init__(energy, counter, nps)

    def _xyz(self):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """

        x = self.arm_length * np.sin(self.angle)
        y = 0.0
        z = self.pivot - self.arm_length * np.cos(self.angle)
        return x, y, z

    def cells(self, detector, electrontrack):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        text = ['C Source cells\n',
                f'201   18 -0.6 -204 -201 202 {detector.importance(electrontrack)}    $ Porous glass cane\n' ,
                f'202   9 -1.45 201 -203 -205  {detector.importance(electrontrack)}   $ Delrin source Casing\n'
                ]
        return text

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return '#201 #202'

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return [18, 9]

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        text = ['C   Source\n',
                f'201   1 PZ -{self.arm_length}  $ Source Front Surface\n',
                f'202   1 PZ -{self.arm_length + self.source_thickness}  $ Source Back Surface\n',
                f'203   1 PZ -{self.arm_length - self.front_surface_thickness}  $ Capsule front surface\n',
                f'204   1 CZ  {self.source_radius}  $ Source radius\n',
                f'205   1 CZ  {self.capsule_radius}  $ Capsule radius approx.\n',
                ]
        return text

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        cosa = np.cos(self.angle) if np.abs(np.cos(self.angle)) > 1e-15 else 0.0
        sina = np.sin(self.angle)
        text = ['C   Source Transformation\n',
                f'TR1  0.0 0.0 {self.pivot:.8}  {cosa:.8} 0 {sina:.8}  0 1 0  {-sina:.8} 0 {cosa:.8}  1\n']
        return text

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return f'       AXS={-np.sin(self.angle):.8} 0 {np.cos(self.angle) if np.abs(np.cos(self.angle)) > 1e-15 else 0.0:.8}\n'

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return '       EXT=D2\n'

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return '       RAD=D3\n'

    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return f'SI2    -{self.source_thickness} 0\nSP2    -21 0\n'

    def _s3(self):
        """
        The si3 card in MCNP.

        Source extension.

        Returns
        -------
        str
            The SI3 card in MCNP.

        """
        return f'SI3    0 {self.source_radius}\nSP3    -21 1\n'

    def max_radius(self):
        """
        The radius of the world sphere.

        100 or (arm length + pivot) * 1.1, whichever is larger

        Returns
        -------
        float
            The radius of the world sphere.

        """
        if self.arm_length < 100:
            return 100
        return (self.arm_length + self.pivot) *1.10

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            0.0012.

        """
        return 0.0012

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        corners = [np.array([self.x-self.source_radius*np.cos(self.angle), self.y, (self.z-self.source_radius*np.sin(self.angle))]),
                   np.array([self.x-self.source_radius*np.cos(self.angle) + self.source_thickness*np.sin(self.angle), self.y, (self.z-self.source_radius*np.sin(self.angle) - self.source_thickness*np.cos(self.angle))]),
                   np.array([self.x+self.source_radius*np.cos(self.angle), self.y, (self.z+self.source_radius*np.sin(self.angle))]),
                   np.array([self.x-self.source_radius*np.cos(self.angle) + self.source_thickness*np.sin(self.angle), self.y, (self.z+self.source_radius*np.sin(self.angle) - self.source_thickness*np.cos(self.angle))])
                  ]
        return corners


class ZeroD(XD):
    def __init__(self, energy, counter, nps, arm_length, pivot, source_radius=0.165, source_thickness=0.15, front_surface_thickness=0.03, capsule_radius=0.5):
        """
        The 0D geometry.

        The default parameters describes the type c source from EnZ using the ISOCS
        jig at the 0 degree position.

        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        arm_length : float
            Jig arm length.
        pivot : float
            Jig pivot point.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.

        Returns
        -------
        None.

        """
        super().__init__(energy, counter, nps, arm_length, pivot, 0.0, source_radius, source_thickness, front_surface_thickness, capsule_radius)
        self.type = '0D'
        self.marker = 2
        self.FColor = 11
        self.BColor = 11
        if energy < 20:
            self.geometry_error = 0.04
        elif energy < 35:
            self.geometry_error = 0.03
        else:
            self.geometry_error = 0.02


class NinetyD(XD):
    def __init__(self, energy, counter, nps, arm_length, pivot, source_radius=0.165, source_thickness=0.15, front_surface_thickness=0.03, capsule_radius=0.5):
        """
        The 90D geometry.

        The default parameters describes the type c source from EnZ using the ISOCS
        jig at the 90 degree position.


        Parameters
        ----------
         energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        arm_length : float
            Jig arm length.
        pivot : float
            Jig pivot point.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.

        Returns
        -------
        None.

        """
        super().__init__(energy, counter, nps, arm_length, pivot, np.pi/2.0, source_radius, source_thickness, front_surface_thickness, capsule_radius)
        self.type = '90D'
        self.marker = 1
        self.FColor = 3
        self.BColor = 3
        if energy < 45:
            self.geometry_error = 0.2
        elif energy < 100:
            self.geometry_error = 0.1
        elif energy < 200:
            self.geometry_error = 0.07
        elif energy < 300:
            self.geometry_error = 0.05
        else:
            self.geometry_error = 0.04


class OneThirtyFiveD(XD):
    def __init__(self, energy, counter, nps, arm_length, pivot, source_radius=0.165, source_thickness=0.15, front_surface_thickness=0.03, capsule_radius=0.5):
        """
        The 135D geometry.

        The default parameters describes the type c source from EnZ using the ISOCS
        jig at the 135 degree position.


        Parameters
        ----------
         energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        arm_length : float
            Jig arm length.
        pivot : float
            Jig pivot point.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.

        Returns
        -------
        None.

        """

        super().__init__(energy, counter, nps, arm_length, pivot, np.deg2rad(135.0), source_radius, source_thickness, front_surface_thickness, capsule_radius)
        self.type = '135D'
        self.marker = 3
        self.FColor = 10
        self.BColor = 10
        if energy < 45:
            self.geometry_error = 0.25
        elif energy < 100:
            self.geometry_error = 0.15
        elif energy < 500:
            self.geometry_error = 0.1
        else:
            self.geometry_error = 0.07


class FortyFiveD(XD):
    def __init__(self, energy, counter, nps, arm_length, pivot, source_radius=0.165, source_thickness=0.15, front_surface_thickness=0.03, capsule_radius=0.5):
        """
        The 45D geometry.

        The default parameters describes the type c source from EnZ using the ISOCS
        jig at the 45 degree position.


        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        arm_length : float
            Jig arm length.
        pivot : float
            Jig pivot point.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.

        Returns
        -------
        None.

        """

        super().__init__(energy, counter, nps, arm_length, pivot, np.deg2rad(45.0), source_radius, source_thickness, front_surface_thickness, capsule_radius)
        self.type = '45D'
        if energy < 20:
            self.geometry_error = 0.04
        elif energy < 35:
            self.geometry_error = 0.03
        else:
            self.geometry_error = 0.02


class DC(Source):
    def __init__(self, energy, counter, nps, source_radius=0.165, source_thickness=0.15,
                 front_surface_thickness=0.034, capsule_radius=0.5,
                 spacer_thickness=0.2995):
        """
        The DC source position. The default parameters describe a
        EnZ type c source on a 2.995 mm thick plastic spacer

        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.
        spacer_thickness : float, optional
            The thickness of the plastic spacer. The default is 0.2995.

        Returns
        -------
        None.

        """
        self.source_radius = source_radius
        self.source_thickness = source_thickness
        self.front_surface_thickness = front_surface_thickness
        self.capsule_radius = capsule_radius
        self.spacer_thickness = spacer_thickness
        super().__init__(energy, counter, nps)
        self.type = 'DC'
        self.marker = 2
        self.FColor = 29
        self.BColor = -4142
        if energy < 25:
            self.geometry_error = 0.15
        elif energy < 35:
            self.geometry_error = 0.1
        else:
            self.geometry_error = 0.025

    def _xyz(self):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """
        z = -(self.spacer_thickness + self.front_surface_thickness)
        return 0.0, 0.0, z

    def cells(self, detector, electrontrack):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        electrontrack : bool
            If true electrontracking will be supported, if False electron
            tracking will not be supported

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        text = ['C Source cells\n',
                f'201   14 -1.17 -201 202 -211  {detector.importance(electrontrack)} $ Plastic Spacer\n',
                f'202   9 -1.45 -202 203 -206  {detector.importance(electrontrack)} $ rectangular source mat\n',
                f'203   18 -0.6 -203 204 -205 {detector.importance(electrontrack)} $ porous glass cane\n'
                ]
        return text

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return '#201 #202 #203'

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return [14, 18, 9]

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        text = ['C Source surfaces\n',
                '201  PZ -0.0001 $ Filter Paper - bottom of plastic spacer\n',
                f'202  PZ -{self.spacer_thickness:.6} $ Filter Paper - top of plastic spacer\n',
                f'203  PZ -{self.spacer_thickness + self.front_surface_thickness:.6} $ Rectangular Source delrin material\n',
                f'204  PZ -{self.spacer_thickness + self.front_surface_thickness + self.source_thickness:.6} $ porous glass cane thickness\n',
                f'205  CZ {self.source_radius:.6} $ porous glass cane radius\n',
                f'206  CZ {self.capsule_radius:.6} $ Capsule radius\n',
                '211  CZ  4.85750 $ Filter Paper - Plastic Spacer\n'
                ]
        return text

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        return ''

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return '       AXS=0 0 1\n'

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return '       EXT=D2\n'

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return '       RAD=D3\n'

    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return f'SI2    -{self.source_thickness} 0\nSP2    -21 0\n'

    def _s3(self):
        """
        The si3 card in MCNP.

        Source extension.

        Returns
        -------
        str
            The SI3 card in MCNP.

        """
        return f'SI3    0 {self.source_radius}\nSP3    -21 1\n'

    def weight(self, detector=None, full_detector=None):
        """
        The source emits photons in 2pie steradians

        Overrides the parent method

        Parameters
        ----------
        detector : Detector, optional
            Not used. The default is None.
        full_detector : bool, optional
            Not used. The default is None.

        Returns
        -------
        float
            0.5.

        """
        return 0.5

    def max_radius(self, detector=None):
        """
        The radius of the world sphere.

        100

        Returns
        -------
        float
            The radius of the world sphere.

        """
        return 100

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            0.0012.

        """
        return 0.0012

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        corners = [np.array([-self.source_radius, self.y, self.z]),
                   np.array([-self.source_radius, self.y, self.z - self.source_thickness]),
                   np.array([self.source_radius, self.y, self.z]),
                   np.array([self.source_radius, self.y, self.z - self.source_thickness])
                  ]
        return corners


class DF(Source):
    def __init__(self, energy, counter, nps, source_radius=0.165, source_thickness=0.15,
                 front_surface_thickness=0.034, capsule_radius=0.5,
                 bottom_spacer_thickness=0.285, void_thickness=9.49,
                 top_spacer_thickness=0.585):
        """


        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.
        bottom_spacer_thickness : float, optional
            The thickness of the bottom spacer. The default is 0.285.
        void_thickness : float, optional
            The thickness of the void in the center of the spacer. The default is 9.49.
        top_spacer_thickness : float, optional
            The thickness of the top spacer. The default is 0.585.

        Returns
        -------
        None.

        """
        self.source_radius = source_radius
        self.source_thickness = source_thickness
        self.front_surface_thickness = front_surface_thickness
        self.capsule_radius = capsule_radius
        self.bottom_spacer_thickness = bottom_spacer_thickness
        self.void_thickness = void_thickness
        self.top_spacer_thickness = top_spacer_thickness
        super().__init__(energy, counter, nps)
        self.type = 'DF'
        self.marker = 1
        self.FColor = 30
        self.BColor = -4142
        if energy < 25:
            self.geometry_error = 0.15
        elif energy < 35:
            self.geometry_error = 0.1
        else:
            self.geometry_error = 0.02

    def _xyz(self):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """
        z = -(self.bottom_spacer_thickness + self.void_thickness + self.top_spacer_thickness + self.front_surface_thickness)
        return 0.0, 0.0, z

    def cells(self, detector, electrontrack):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        text = ['C Source cells\n',
                f'201   14 -1.17 -201 202 -211 {detector.importance(electrontrack)} $ Plastic Spacer\n',
                f'202   3 -0.0012 -202 203 -211 {detector.importance(electrontrack)} $ air gap\n',
                f'203   14 -1.17 -203 204 -211 {detector.importance(electrontrack)} $ far spacer\n',
                f'204   9 -1.45 -204 205 -208 {detector.importance(electrontrack)} $ rectangular source capsule mat\n',
                f'205   18 -0.6 -205 206 -207 {detector.importance(electrontrack)} $ porous glass cane\n'
                ]
        return text

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return '#201 #202 #203 #204 #205'

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return [3, 9, 14, 18]

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        text = ['C Source surfaces\n',
                '201  PZ -0.0001 $ Filter Paper - bottom of plastic spacer\n',
                f'202  PZ -{self.bottom_spacer_thickness} $ Filter Paper - spacer-air boundary\n',
                f'203  PZ -{self.bottom_spacer_thickness + self.void_thickness} $ Filter Paper - air-more spacer boundary\n',
                f'204  PZ -{self.bottom_spacer_thickness + self.void_thickness + self.top_spacer_thickness} $ Filter Paper - far side of spacer\n',
                f'205  PZ -{self.bottom_spacer_thickness + self.void_thickness + self.top_spacer_thickness + self.front_surface_thickness} $ Rectangular capsule delrin material\n',
                f'206  PZ -{self.bottom_spacer_thickness + self.void_thickness + self.top_spacer_thickness + self.front_surface_thickness + self.source_thickness} $ Porous glass cane thickness\n',
                f'207  CZ {self.source_radius} $ Porous glass cane radius\n',
                f'208  CZ {self.capsule_radius} $ Capsule radius\n',
                '211  CZ  4.85750 $ Filter Paper - Plastic Spacer\n'
                ]
        return text

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        return ''

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return '       AXS=0 0 1\n'

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return '       EXT=D2\n'

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return '       RAD=D3\n'

    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return f'SI2    -{self.source_thickness} 0\nSP2    -21 0\n'

    def _s3(self):
        """
        The si3 card in MCNP.

        Source extension.

        Returns
        -------
        str
            The SI3 card in MCNP.

        """
        return f'SI3    0 {self.source_radius}\nSP3    -21 1\n'

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        corners = [np.array([-self.source_radius, self.y, self.z]),
                   np.array([-self.source_radius, self.y, self.z - self.source_thickness]),
                   np.array([self.source_radius, self.y, self.z]),
                   np.array([self.source_radius, self.y, self.z - self.source_thickness])
                  ]
        return corners

    def max_radius(self, detector=None):
        """
        The radius of the world sphere.

        100

        Returns
        -------
        float
            The radius of the world sphere.

        """
        return 100

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            0.0012.

        """
        return 0.0012


class DR(Source):
    def __init__(self, energy, counter, nps, distance=25.0, source_radius=0.165, source_thickness=0.15,
                 front_surface_thickness=0.03, capsule_radius=0.5):
        """
        A source on the detector axis.

        Default values corresponds to a EnZ type C source at 25 cm.

        The name comes from the relative efficiency measurement in ISOCS.

        Parameters
        ----------
         energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
       distance : float, optional
            The distance from the end cap to the source. The default is 25.0.
        source_radius : float, optional
            The source radius. The default is 0.165.
        source_thickness : float, optional
            The source thickness. The default is 0.15.
        front_surface_thickness : float, optional
            Thickness of front surface. The default is 0.03.
        capsule_radius : float, optional
            the radius of the source capsule. The default is 0.5.

        Returns
        -------
        None.

        """
        self.distance = distance
        super().__init__(energy, counter, nps)
        self.source_radius = source_radius
        self.source_thickness = source_thickness
        self.front_surface_thickness = front_surface_thickness
        self.capsule_radius = capsule_radius
        #self.energies = [1332.5]
        self.type = 'DR'
        self.geometry_error = 0.02
        self.marker = 9
        self.FColor = 1
        self.BColor = 1

    def _xyz(self):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """
        return 0.0, 0.0, -self.distance

    def cells(self, detector, electrontrack):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        text = ['C Source cells\n',
                f'201   18 -0.6 -204 -201 202 {detector.importance(electrontrack)} $ Porous glass cane\n',
                f'202   9 -1.45 201 -203 -205  {detector.importance(electrontrack)} $ Delrin source Casing\n'
                ]
        return text

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return '#201 #202'

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return [18, 9]

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        text = ['C   Source\n',
                f'201   PZ -{self.distance} $ Source Front Surface\n',
                f'202   PZ -{self.distance + self.source_thickness} $ Source Back Surface\n',
                f'203   PZ -{self.distance - self.front_surface_thickness} $ Capsule front surface\n',
                f'204   CZ  {self.source_radius} $ Source radius\n',
                f'205   CZ  {self.capsule_radius} $ Capsule radius approx.\n',
                ]
        return text

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return '       AXS=0 0 1\n'

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return '       EXT=D2\n'

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return '       RAD=D3\n'

    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return f'SI2    -{self.source_thickness} 0\nSP2    -21 0\n'

    def _s3(self):
        """
        The si3 card in MCNP.

        Source extension.

        Returns
        -------
        str
            The SI3 card in MCNP.

        """
        return f'SI3    0 {self.source_radius}\nSP3    -21 1\n'

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        return ''

    def max_radius(self):
        """
        The radius of the world sphere.

        100

        Returns
        -------
        float
            The radius of the world sphere.

        """
        return 100

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            0.0012.

        """
        return 0.0012

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        corners = [np.array([-self.source_radius, 0.0, self.z]),
                   np.array([-self.source_radius, 0.0, self.z - self.source_thickness]),
                   np.array([self.source_radius, 0.0, self.z]),
                   np.array([self.source_radius, 0.0, self.z - self.source_thickness])
                  ]
        return corners


class WE(Source):
    def __init__(self, energy, counter, nps, well_bottom, inner_radius=0.4875,
                 outer_radius=0.5875, fill_height=1.5019):
        """
        The source used for the well characterization (WE) measurement

        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        well_bottom : float
            The reference point of the endcap well bottom.


        """
        self.well_bottom = well_bottom
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.fill_height = fill_height
        super().__init__(energy, counter, nps, well_source=True)
        self.type = 'WE'
        #TODO: Look up these values
        self.marker = 5
        self.FColor = 23
        self.BColor = 23
        if energy < 25:
            self.geometry_error = 0.045
        elif energy < 30:
            self.geometry_error = 0.030
        else:
            self.geometry_error = 0.025


    def cells(self, detector, electrontrack):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        electrontrack : bool
            If true electrontracking will be supported, if False electron
            tracking will not be supported

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        text = ['C Source cells\n',
                f'201   20 -0.91 (-203 204 205 -206):(-201 202 206)  {detector.importance(electrontrack)} $ Vial\n',
                f'202   19 -1.15  -202:(-206 -204 207)  {detector.importance(electrontrack)} $ Source\n',
                f'203   19 -1.15  -207 -204 205 {detector.importance(electrontrack)} $ Non-radioactive resin\n'
                ]
        return text

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return '#201 #202 #203'

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return [19, 20]

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        text = ['C Source surfaces\n',
                f'201  SZ {self.well_bottom - self.outer_radius} {self.outer_radius}  $ Sample bottom outside curvature\n',
                f'202  SZ {self.well_bottom - self.outer_radius} {self.inner_radius}  $ Sample bottom inside curvature\n',
                f'203  CZ {self.outer_radius} $ Vial outside\n',
                f'204  CZ {self.inner_radius} $ Vial inside\n',
                f'205  PZ -3.35   $ Top of vial\n',
                f'206  PZ {self.well_bottom - self.outer_radius} $ Boundary between vial bottom and side\n',
                f'207  PZ {self.well_bottom - self.fill_height} $ Boundary between radioactive and non radioactive matrix\n'
                ]

        return text

    def max_radius(self):
        return 50

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            0.0012.

        """
        return 0.0012

    def _xyz(self):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """

        x = 0.0
        y = 0.0
        z = self.well_bottom - self.fill_height - 0.1
        return x, y, z

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return '       AXS=0 0 1\n'

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return '       EXT=D2\n'

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return '       RAD=D1\n'


    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return f'SI2    0 1.6\nSP2    -21 0\n'


    def _s3(self):
        """
        Not used for the well source

        Returns
        -------
        str
            Empty string.

        """
        return ''

    def _cell_card(self):
        return '       CEL=202\n'

    def _vec(self, detector, full_detector):
        """
        The vec card for the MCNP source.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        str
            Empty string.

        """
        return ''

    def _dir(self):
        """
        The DIR card for the MCNP source

        Returns
        -------
        str
            Empty string.

        """
        return ''

    def weight(self, detector, full_detector=True):
        """
        The well source can emit photons in all directions. Therefore the
        weight is always 1.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        weight : float
            1.0

        """

        return 1.0

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        return []

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        return ''
    def _s1(self, detector, full_detector):
        """
        The well detector uses the s1 distribution for the source extension

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        str
            The source extension

        """
        return 'SI1    0 0.4875\nSP1    -21 1\n'


class PointSource(Source):
    def __init__(self, energy, counter, nps, x, y, z):
        """
        A point source in vacuum.

        Parameters
        ----------
        energy : float
            Emission energy.
        counter : Integer
            Source counter.
        nps : float
            Number of particles in MCNP.
        x : float
            x coordinate of the source.
        y : float
            y coordinate of the source.
        z : float
            z coordinate of the source.

        Returns
        -------
        None.

        """
        self.x = x
        self.y = y
        self.z = z
        super().__init__(energy, counter, nps)
        self.type = 'Point'

    def _xyz(self, detector=None):
        """
        The cartesian coordinates of the source reference point

        Returns
        -------
        x : float
            The x coordinate.
        y : float
            The y coordinate.
        z : float
            The z coordinate.

        """
        return self.x, self.y, self.z

    def cells(self, detector=None, electrontrack=None):
        """
        The cells describing the source in MCNP.

        Parameters
        ----------
        detector : Detector
            The detector that the source is used with.
        full_detector : bool, optional
            If True the directional bias algorithm includes the entire detector, if False only the
            crystal is included in the directional bias. The default is True.

        Returns
        -------
        text : List
            A list of the cells describing the source.

        """
        return ''

    def cell_numbers(self):
        """
        The cell numbers with # infront of them so that MCNP knows
        to exclude the cells.

        Returns
        -------
        str
            The cell numbers with # in front of them.

        """
        return ''

    def material_numbers(self):
        """
        A list of material numbers used in MCNP for the source.

        Returns
        -------
        list
            The MCNP material numbers.

        """
        return []

    def surfaces(self):
        """
        The MCNP surfaces used to describe the source.

        Returns
        -------
        List
            A list of strings of surfaces.

        """
        return ''

    def transformation(self):
        """
        The transformation card in MCNP.

        Returns
        -------
        text : List
            The transformation card in MCNP.

        """
        return ''

    def _axs(self):
        """
        The axs card in MCNP.

        Returns
        -------
        str
            The axs card in MCNP.

        """
        return ''

    def _ext(self):
        """
        The ext card in MCNP.

        Returns
        -------
        str
            The ext card in MCNP.

        """
        return ''

    def _rad(self):
        """
        The rad card in MCNP

        Returns
        -------
        str
            The rad card in MCNP.

        """
        return ''

    def _s2(self):
        """
        The si2 card in MCNP

        Source extension

        Returns
        -------
        str
            The si2 card in MCNP.

        """
        return ''

    def _s3(self):
        """
        The si3 card in MCNP.

        Source extension.

        Returns
        -------
        str
            The SI3 card in MCNP.

        """
        return ''

    def _source_corners(self):
        """
        The corners of the source in cartesian coordinates.
        Used for the directional bias algorithm.

        Returns
        -------
        corners : List
            List of np.arrays of the corners of the source.

        """
        return [np.array([self.x, self.y, self.z])]

    def max_radius(self):
        """
        The radius of the world sphere.

        100 or the distance from the origin to the reference point mutliplied with 1.1

        Returns
        -------
        float
            The radius of the world sphere.

        """
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2) *1.10
        return r if r > 100.0 else 100.0

    def air_density(self):
        """
        The density of the air for the source.

        Returns
        -------
        float
            1.2e-12.

        """
        return 1.2e-12

# Dictionary that maps the names on the ISOCS spreadsheet to
# source classes.
name_dictionary = {'0D':ZeroD, '90D':NinetyD, '135D':OneThirtyFiveD, 'DC':DC,
                   'DF':DF, 'RELEFF':DR, '45D':FortyFiveD, 'WE':WE}
