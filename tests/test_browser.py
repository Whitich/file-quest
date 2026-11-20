import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from retro_file_explorer import RetroExplorer

class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'folder').mkdir()
        (self.root / 'hello.txt').write_text('Merhaba dünya', encoding='utf-8')
        (self.root / '.private').write_text('hidden')
        self.app = RetroExplorer(str(self.root))
    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()
    def select(self, name):
        self.app.index = next(i for i, e in enumerate(self.app.entries) if e['name'] == name)
        self.app.rebuild_preview()
    def test_sort_and_hidden_toggle(self):
        self.assertEqual(self.app.entries[0]['name'], 'folder')
        self.assertNotIn('.private', [e['name'] for e in self.app.entries])
        self.app.on_key(pygame.K_h)
        self.assertIn('.private', [e['name'] for e in self.app.entries])
    def test_utf8_preview(self):
        self.select('hello.txt')
        self.assertEqual(self.app.pv_kind, 'text')
        self.assertIn('Merhaba dünya', self.app.pv_lines)
    def test_refresh_clears_stale_image(self):
        self.app.img_cache['stale'] = object()
        self.app.load_dir()
        self.assertFalse(self.app.img_cache)
    def test_folder_navigation(self):
        self.select('folder')
        self.app.activate()
        self.assertEqual(Path(self.app.cwd), self.root / 'folder')
        self.app.go_up()
        self.assertEqual(Path(self.app.cwd), self.root)
    def test_failed_home_preserves_location(self):
        with patch('os.path.expanduser', return_value=str(self.root / 'missing')):
            self.app.go_home()
        self.assertEqual(Path(self.app.cwd), self.root)
    def test_mouse_double_click_enters_folder(self):
        point = (30, 130)
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.app.run()
        self.assertEqual(Path(self.app.cwd), self.root / 'folder')
    def test_draw_and_open_failure(self):
        self.select('hello.txt')
        self.app.draw()
        self.app.pending = str(self.root / 'hello.txt')
        with patch('os.startfile', create=True, side_effect=OSError('test failure')):
            self.app.do_open()
        self.assertIn('test failure', self.app.msg)

if __name__ == '__main__':
    unittest.main()
