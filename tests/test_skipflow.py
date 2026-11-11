import json
import tempfile
import unittest
from pathlib import Path

from randomizer.skipflow import SkipTable

DROP = ['EventWait', 'EventTalk', 'EventMoveToTargetPosCamera',
        'EventMoveCameraAnimationInstructionsForFlowchart', 'EventPlayAS',
        'EventPlayerPlayASForFlowchart', 'EventPlayASWithClothWarp',
        'EventDemoProductSupportComment', 'EventSetAdvancedDoFForFlowchart',
        'EventTriggerEmitXLink', 'EventTriggerXLinkFadeByKey',
        'EventTriggerControllerRumble', 'EventNaviLookAtObject',
        'EventCloseMessageDialog', 'EventDoNothing']
KEEP = ['EventTriggerSetGameDataBool', 'EventTriggerSetEventBool',
        'EventTriggerAddOrRemovePouchContent', 'EventTransition',
        'EventWarpToTargetPosAndRot', 'EventPlayerWarpToTargetPosAndRot',
        'EventEventFadeOut', 'EventEventFadeIn', 'EventTriggerRequestAutoSave',
        'EventNotARealAction']


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = SkipTable.load()

    def test_drop(self):
        for a in DROP:
            self.assertFalse(self.t.keeps(None, a), a)

    def test_keep(self):
        for a in KEEP:
            self.assertTrue(self.t.keeps(None, a), a)

    def test_unknown_query(self):
        self.assertIs(self.t.collapses('NotARealQuery'), False)

    def test_subflows(self):
        for f, e in (('GetPouchContent', 'DisplayGetByActorName'),
                     ('Dm_SY_Ocarina', 'LearningOcarinaFollowExample'),
                     ('Common_Camera_Pln', 'CameraDoF_Default')):
            self.assertTrue(self.t.drops_subflow(f, e), (f, e))
        for f, e in (('GetPouchContent', 'GetPouchContentByActorName'),
                     ('Dm_SY_GetInEvent', 'GetInEvent_Zeldaletter')):
            self.assertFalse(self.t.drops_subflow(f, e), (f, e))

    def test_actor_override(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 't.json'
            p.write_text(json.dumps({
                'actions': {'EventX': 'drop', 'EventR': 'review'},
                'actor_actions': {'Npc.EventX': 'keep'},
                'queries': {'Q': 'collapse', 'S': 'state'},
                'subflows_drop': [], 'counts': {}}))
            t = SkipTable.load(p)
        self.assertTrue(t.keeps('Npc', 'EventX'))
        self.assertFalse(t.keeps('Other', 'EventX'))
        self.assertFalse(t.keeps(None, 'EventX'))
        self.assertTrue(t.keeps(None, 'EventR'))
        self.assertTrue(t.collapses('Q'))
        self.assertFalse(t.collapses('S'))


if __name__ == '__main__':
    unittest.main()
