"""Radial mapping and paired Linux reports, without requiring input devices."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.inputs import Inputs

class AnalogTests(unittest.TestCase):
    def test_circular_mapping(self):
        backend=Inputs(True);backend.mode='gamepad'
        for deadzone in (0,.12,.4):
            backend.deadzone=deadzone
            for stick,codes in [('LEFT',(0,1)),('RIGHT',(3,4))]:
                for degrees in range(360):
                    angle=math.radians(degrees)
                    backend.axis(stick,math.cos(angle),math.sin(angle))
                    values=[backend.axes[c] for c in codes]
                    self.assertLessEqual(math.hypot(*values),32768)
                    for value,expected in zip(values,(math.cos(angle),math.sin(angle))):
                        self.assertAlmostEqual(value/32767,expected,places=4)
                backend.axis(stick,deadzone/2,deadzone/2)
                self.assertEqual([backend.axes[c] for c in codes],[0,0])
                backend.axis(stick,1,1)
                self.assertAlmostEqual(math.hypot(*(backend.axes[c] for c in codes)),32767,delta=1)
        backend.deadzone=.12;backend.axis('LEFT',.65,.08)
        self.assertGreater(backend.axes[0],0);self.assertGreater(backend.axes[1],0)

    def test_one_syn_per_pair_and_click_independence(self):
        class Device:
            def __init__(self):self.events=[]
            def write(self,*args):self.events.append(args)
            def syn(self):self.events.append('SYN')
        backend=Inputs(True);backend.mode='gamepad';backend.fake=False;backend.gamepad=Device()
        backend.axis('LEFT',.6,.6)
        self.assertEqual(len(backend.gamepad.events),3)
        self.assertEqual(backend.gamepad.events[-1],'SYN')
        axes=dict(backend.axes)
        for button in ('L3','R3'):
            backend.button(button,'down');backend.button(button,'up')
            self.assertEqual(backend.axes,axes)

if __name__=='__main__':unittest.main()
