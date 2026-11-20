import os
import sys
import math
import struct
import time
import textwrap
from datetime import datetime

try:
    import pygame
except ImportError:
    print("[X] pygame bulunamadi.  Kurulum:  python -m pip install pygame-ce")
    sys.exit(1)

W, H = 1000, 640
HDR, FTR = 76, 64
PANEL_Y = HDR + 14
PANEL_H = H - PANEL_Y - FTR - 14
LEFT_X, LEFT_W = 20, 560
RIGHT_X = 596
RIGHT_W = W - RIGHT_X - 20

BLACK = (0, 0, 0)
BG = (8, 8, 20)
PANEL = (14, 14, 34)
HEADBAND = (24, 24, 54)
EDGE = (70, 70, 130)
GREEN = (60, 255, 140)
MAG = (255, 80, 200)
CYAN = (90, 220, 255)
YEL = (255, 225, 90)
WHITE = (235, 235, 245)
GREY = (130, 130, 165)
RED = (255, 90, 90)

TEXT_EXT = {
    ".txt", ".py", ".md", ".json", ".csv", ".log", ".ini", ".cfg", ".bat",
    ".ps1", ".html", ".css", ".js", ".ts", ".xml", ".yml", ".yaml", ".toml",
    ".sh", ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".sql", ".srt",
    ".nfo", ".reg", ".env", ".gitignore", ".rst", ".in", ".properties",
}
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico", ".tga"}


def format_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


def fit_name(name, max_chars):
    if len(name) <= max_chars:
        return name
    return name[: max_chars - 2] + ".."


class RetroExplorer:
    def __init__(self, start_dir=None):
        pygame.init()
        self.mixer_ok = False
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            self.mixer_ok = True
        except Exception:
            pass
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("FILE QUEST - RETRO EXPLORER")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_head = pygame.font.SysFont("consolas", 21, bold=True)
        self.font_list = pygame.font.SysFont("consolas", 20)
        self.font_small = pygame.font.SysFont("consolas", 15)
        self.font_pre = pygame.font.SysFont("consolas", 15)
        self.font_load = pygame.font.SysFont("consolas", 42, bold=True)

        self.sfx_move = None
        self.sfx_ok = None
        self.sfx_back = None
        self.sfx_open = None
        if self.mixer_ok:
            self.sfx_move = self.make_tone(880, 45, 0.10)
            self.sfx_ok = self.make_tone(1320, 70, 0.12)
            self.sfx_back = self.make_tone(440, 90, 0.12)
            self.sfx_open = self.make_tone(660, 140, 0.14)
        self.sound_on = True

        self.show_hidden = False
        self.cwd = os.path.abspath(start_dir or os.path.expanduser("~"))
        self.entries = []
        self.index = 0
        self.scroll = 0
        self.msg = ""
        self.dirty = True
        self.pv_kind = ""
        self.pv_lines = []
        self.pv_img = None
        self.pv_off = 0
        self.pv_meta = ""
        self.pv_name = ""
        self.img_cache = {}
        self.opening = False
        self.open_t = 0.0
        self.pending = None
        self.t0 = time.time()
        self.last_click = (None, 0)

        self.scan = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(self.scan, (0, 0, 0, 55), (0, y), (W, y))

        self.load_dir()
        self.rebuild_preview()

    @staticmethod
    def make_tone(freq, ms, vol):
        try:
            rate = 22050
            n = int(rate * ms / 1000)
            buf = bytearray()
            for i in range(n):
                env = 1.0
                if i < 300:
                    env = i / 300
                if i > n - 700:
                    env = max(0.0, (n - i) / 700)
                v = int(vol * 32767 * env * math.sin(2 * math.pi * freq * i / rate))
                buf += struct.pack("<h", v)
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    def play(self, which):
        if not self.sound_on:
            return
        snd = {
            "move": self.sfx_move,
            "ok": self.sfx_ok,
            "back": self.sfx_back,
            "open": self.sfx_open,
        }.get(which)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def load_dir(self):
        old_entries, old_index, old_scroll, old_msg = (
            self.entries, self.index, self.scroll, self.msg,
        )
        self.entries = []
        self.img_cache.clear()
        self.msg = ""
        self.index = 0
        self.scroll = 0
        try:
            with os.scandir(self.cwd) as it:
                for e in it:
                    if not self.show_hidden and e.name.startswith("."):
                        continue
                    try:
                        st = e.stat()
                        size, mtime = st.st_size, st.st_mtime
                        is_dir = e.is_dir()
                    except OSError:
                        continue
                    self.entries.append(
                        {"name": e.name, "dir": is_dir, "size": size, "mtime": mtime}
                    )
        except PermissionError:
            self.entries, self.index, self.scroll = old_entries, old_index, old_scroll
            self.msg = "ERISIM YOK - izin verilmedi"
            self.dirty = True
            return False
        except FileNotFoundError:
            self.msg = "KLASOR BULUNAMADI"
            self.entries, self.index, self.scroll = old_entries, old_index, old_scroll
            self.dirty = True
            return False
        except OSError as ex:
            self.msg = f"HATA: {ex}"
            self.entries, self.index, self.scroll = old_entries, old_index, old_scroll
            self.dirty = True
            return False
        self.entries.sort(key=lambda d: (0 if d["dir"] else 1, d["name"].lower()))
        self.dirty = True
        return True

    def rebuild_preview(self):
        self.pv_lines = []
        self.pv_img = None
        self.pv_off = 0
        self.pv_kind = ""
        self.pv_meta = ""
        self.pv_name = ""
        if not self.entries:
            self.pv_kind = "empty"
            self.pv_lines = ["KLASOR BOS"]
            return
        it = self.entries[self.index]
        path = os.path.join(self.cwd, it["name"])
        self.pv_name = it["name"]
        ts = datetime.fromtimestamp(it["mtime"]).strftime("%Y-%m-%d %H:%M")
        self.pv_meta = f"{format_size(it['size'])} | {ts}"
        if it["dir"]:
            self.pv_kind = "dir"
            try:
                with os.scandir(path) as children:
                    count = sum(1 for _ in children)
            except OSError:
                count = "?"
            self.pv_lines = ["KLASOR", "", f"{count} oge"]
            return
        ext = os.path.splitext(it["name"])[1].lower()
        if ext in IMG_EXT:
            self.pv_kind = "image"
            surf = self.img_cache.get(path)
            if surf is None:
                try:
                    surf = pygame.image.load(path)
                    if len(self.img_cache) > 30:
                        self.img_cache.clear()
                    self.img_cache[path] = surf
                except Exception:
                    surf = None
            self.pv_img = surf
            if surf is None:
                self.pv_kind = "binary"
                self.pv_lines = ["RESIM OKUNAMADI"]
            else:
                w, h = surf.get_size()
                self.pv_meta += f" | {w}x{h}"
            return
        if ext in TEXT_EXT or ext == "" or it["name"].lower() in TEXT_EXT:
            raw = b""
            try:
                with open(path, "rb") as f:
                    raw = f.read(65536)
            except OSError as ex:
                self.pv_kind = "binary"
                self.pv_lines = ["OKUNAMADI", "", str(ex)]
                return
            if b"\x00" in raw[:4096]:
                self.pv_kind = "binary"
                self.pv_lines = ["BINARY DOSYA", "", f"Boyut: {format_size(it['size'])}", "", "ONIZLEME YOK"]
                return
            text = raw.decode("utf-8", errors="replace")
            raw_lines = text.splitlines()[:80]
            wrapped = []
            for line in raw_lines:
                parts = textwrap.wrap(line, 40) or [""]
                wrapped.extend(parts)
                if len(wrapped) >= 150:
                    break
            if not wrapped:
                wrapped = ["(bos dosya)"]
            self.pv_kind = "text"
            self.pv_lines = wrapped
            return
        self.pv_kind = "binary"
        self.pv_lines = [
            "BINARY DOSYA",
            "",
            f"Boyut: {format_size(it['size'])}",
            f"Tip: {ext or 'bilinmiyor'}",
            "",
            "ONIZLEME YOK",
        ]

    def move(self, delta):
        if not self.entries:
            return
        new = self.index + delta
        new = max(0, min(len(self.entries) - 1, new))
        if new != self.index:
            self.index = new
            self.dirty = True
            self.play("move")

    def activate(self):
        if not self.entries:
            return
        it = self.entries[self.index]
        path = os.path.join(self.cwd, it["name"])
        if it["dir"]:
            target = os.path.normpath(path)
            old = self.cwd
            self.cwd = target
            if self.load_dir():
                self.play("ok")
                self.rebuild_preview()
            else:
                self.cwd = old
                self.load_dir()
                self.rebuild_preview()
                self.play("back")
        else:
            self.opening = True
            self.open_t = time.time()
            self.pending = path
            self.play("open")

    def do_open(self):
        path = self.pending
        self.pending = None
        self.opening = False
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                import subprocess

                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, path])
        except OSError as ex:
            self.msg = f"ACILAMADI: {ex}"

    def go_up(self):
        parent = os.path.dirname(os.path.normpath(self.cwd))
        if parent and parent != self.cwd:
            old = self.cwd
            self.cwd = parent
            if self.load_dir():
                self.play("back")
                self.rebuild_preview()
            else:
                self.cwd = old
                self.load_dir()
                self.rebuild_preview()

    def go_home(self):
        home = os.path.expanduser("~")
        if os.path.normpath(home) != os.path.normpath(self.cwd):
            old = self.cwd
            self.cwd = home
            if self.load_dir():
                self.play("ok")
                self.rebuild_preview()
            else:
                self.cwd = old

    def scroll_preview(self, delta):
        max_off = max(0, len(self.pv_lines) - 6)
        self.pv_off = max(0, min(max_off, self.pv_off + delta))

    def on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.quit()
            sys.exit()
        if key == pygame.K_UP:
            self.move(-1)
        elif key == pygame.K_DOWN:
            self.move(1)
        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            if not self.opening:
                self.activate()
        elif key == pygame.K_BACKSPACE:
            self.go_up()
        elif key == pygame.K_F5:
            if self.load_dir():
                self.play("ok")
            self.rebuild_preview()
        elif key == pygame.K_h:
            self.show_hidden = not self.show_hidden
            self.load_dir()
            self.rebuild_preview()
            self.play("ok")
        elif key == pygame.K_s:
            self.sound_on = not self.sound_on
            if self.sound_on:
                self.play("ok")
        elif key == pygame.K_HOME:
            self.go_home()
        elif key == pygame.K_PAGEUP:
            self.scroll_preview(-8)
        elif key == pygame.K_PAGEDOWN:
            self.scroll_preview(8)
        elif key == pygame.K_LEFT:
            self.scroll_preview(-2)
        elif key == pygame.K_RIGHT:
            self.scroll_preview(2)

    @staticmethod
    def draw_icon(surf, x, y, is_dir, color):
        if is_dir:
            pygame.draw.rect(surf, color, (x, y + 4, 18, 11))
            pygame.draw.rect(surf, color, (x, y, 9, 5))
            pygame.draw.rect(surf, BLACK, (x + 2, y + 7, 14, 5))
            pygame.draw.rect(surf, color, (x + 3, y + 8, 12, 3))
        else:
            pygame.draw.rect(surf, color, (x + 2, y, 13, 17), 2)
            pygame.draw.line(surf, color, (x + 5, y + 5), (x + 12, y + 5), 1)
            pygame.draw.line(surf, color, (x + 5, y + 8), (x + 12, y + 8), 1)
            pygame.draw.line(surf, color, (x + 5, y + 11), (x + 10, y + 11), 1)

    def draw(self):
        s = self.screen
        s.fill(BG)
        now = time.time()

        pygame.draw.rect(s, (10, 10, 26), (0, 0, W, HDR))
        pygame.draw.line(s, MAG, (0, HDR - 3), (W, HDR - 3), 3)
        title = self.font_title.render("FILE QUEST", True, CYAN)
        s.blit(title, (24, 14))
        s.blit(title, (22, 12))
        sub = self.font_small.render("RETRO EXPLORER v1.1", True, GREY)
        s.blit(sub, (24, 54))
        if int(now * 2) % 2 == 0:
            coin = self.font_small.render("INSERT COIN", True, YEL)
            s.blit(coin, (W // 2 - coin.get_width() // 2, 30))
        shown = self.cwd if len(self.cwd) <= 52 else "..." + self.cwd[-49:]
        path_t = self.font_small.render(shown, True, GREEN)
        s.blit(path_t, (W - 22 - path_t.get_width(), 30))

        pygame.draw.rect(s, PANEL, (LEFT_X, PANEL_Y, LEFT_W, PANEL_H))
        pygame.draw.rect(s, EDGE, (LEFT_X, PANEL_Y, LEFT_W, PANEL_H), 2)
        pygame.draw.rect(s, HEADBAND, (LEFT_X + 3, PANEL_Y + 3, LEFT_W - 6, 26))
        hd = self.font_small.render("PLAYER 1 - DOSYALAR", True, GREEN)
        s.blit(hd, (LEFT_X + 12, PANEL_Y + 8))

        list_y = PANEL_Y + 36
        row_h = 26
        visible = (PANEL_H - 44) // row_h
        if self.index < self.scroll:
            self.scroll = self.index
        if self.index >= self.scroll + visible:
            self.scroll = self.index - visible + 1
        max_scroll = max(0, len(self.entries) - visible)
        self.scroll = max(0, min(max_scroll, self.scroll))

        if not self.entries:
            nt = self.font_list.render(self.msg or "BOS", True, RED)
            s.blit(nt, (LEFT_X + 24, list_y + 20))
        else:
            for i in range(self.scroll, min(len(self.entries), self.scroll + visible)):
                it = self.entries[i]
                y = list_y + (i - self.scroll) * row_h
                selected = i == self.index
                if selected:
                    pygame.draw.rect(
                        s, WHITE, (LEFT_X + 6, y, LEFT_W - 12, row_h - 2)
                    )
                icon_color = BLACK if selected else (YEL if it["dir"] else GREY)
                self.draw_icon(s, LEFT_X + 14, y + 4, it["dir"], icon_color)
                name_color = BLACK if selected else (CYAN if it["dir"] else WHITE)
                nm = self.font_list.render(
                    fit_name(it["name"], 40), True, name_color
                )
                s.blit(nm, (LEFT_X + 44, y + 3))

        pygame.draw.rect(s, (18, 18, 40), (RIGHT_X, PANEL_Y, RIGHT_W, PANEL_H))
        pygame.draw.rect(s, EDGE, (RIGHT_X, PANEL_Y, RIGHT_W, PANEL_H), 3)
        pygame.draw.rect(
            s, (50, 50, 100), (RIGHT_X + 7, PANEL_Y + 7, RIGHT_W - 14, PANEL_H - 14), 1
        )
        for cx, cy in (
            (RIGHT_X + 4, PANEL_Y + 4),
            (RIGHT_X + RIGHT_W - 10, PANEL_Y + 4),
            (RIGHT_X + 4, PANEL_Y + PANEL_H - 10),
            (RIGHT_X + RIGHT_W - 10, PANEL_Y + PANEL_H - 10),
        ):
            pygame.draw.circle(s, GREY, (cx + 3, cy + 3), 3)

        name_y = PANEL_Y + 14
        wrapped_name = textwrap.wrap(self.pv_name or "(secim yok)", 32)[:2]
        if not wrapped_name:
            wrapped_name = ["(secim yok)"]
        for wl in wrapped_name:
            nt = self.font_head.render(wl, True, WHITE)
            s.blit(nt, (RIGHT_X + 18, name_y))
            name_y += 26
        if self.pv_meta:
            mt = self.font_small.render(self.pv_meta, True, GREY)
            s.blit(mt, (RIGHT_X + 18, name_y + 2))
            name_y += 24
        pygame.draw.line(s, EDGE, (RIGHT_X + 18, name_y + 4), (RIGHT_X + RIGHT_W - 18, name_y + 4), 2)
        content_y = name_y + 14
        content_h = PANEL_Y + PANEL_H - 18 - content_y
        content_rect = pygame.Rect(RIGHT_X + 16, content_y, RIGHT_W - 32, content_h)

        if self.pv_kind == "image" and self.pv_img is not None:
            img = self.pv_img
            iw, ih = img.get_size()
            if iw > 0 and ih > 0:
                scale = min(
                    content_rect.w / max(iw, 1), content_rect.h / max(ih, 1), 1.0
                )
                tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
                try:
                    scaled = pygame.transform.smoothscale(img.convert_alpha(), (tw, th))
                except Exception:
                    try:
                        scaled = pygame.transform.scale(img, (tw, th))
                    except Exception:
                        scaled = None
                if scaled is not None:
                    px = content_rect.x + (content_rect.w - tw) // 2
                    py = content_rect.y + (content_rect.h - th) // 2
                    s.fill(BLACK, content_rect)
                    s.blit(scaled, (px, py))
        else:
            s.set_clip(content_rect)
            ty = content_rect.y
            for line in self.pv_lines[self.pv_off :]:
                pt = self.font_pre.render(line, True, GREEN)
                s.blit(pt, (content_rect.x + 4, ty))
                ty += 19
                if ty > content_rect.bottom:
                    break
            s.set_clip(None)

        pygame.draw.rect(s, (10, 10, 26), (0, H - FTR, W, FTR))
        pygame.draw.line(s, GREEN, (0, H - FTR), (W, H - FTR), 2)
        keys = "ENTER / CIFT TIK:AC   BACKSPACE:UST   F5:YENILE   H:GIZLI   S:SES   HOME:EV   ESC:CIK"
        kt = self.font_small.render(keys, True, GREY)
        s.blit(kt, (20, H - 47))
        if self.msg:
            mt = self.font_small.render(self.msg, True, RED)
            s.blit(mt, (W - 20 - mt.get_width(), H - 24))
        else:
            st = self.font_small.render(
                f"{len(self.entries)} oge | GIZLI:{'ACIK' if self.show_hidden else 'KAPALI'} | SES:{'ACIK' if self.sound_on else 'KAPALI'}",
                True,
                CYAN,
            )
            s.blit(st, (W - 20 - st.get_width(), H - 24))

        s.blit(self.scan, (0, 0))

        if self.opening:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 215))
            s.blit(ov, (0, 0))
            if int(now * 6) % 2 == 0:
                lt = self.font_load.render("NOW LOADING", True, YEL)
                s.blit(lt, (W // 2 - lt.get_width() // 2, H // 2 - 60))
            nm = self.font_head.render(fit_name(self.pending or "", 48), True, WHITE)
            s.blit(nm, (W // 2 - nm.get_width() // 2, H // 2 + 10))

    def run(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    self.on_key(ev.key)
                elif ev.type == pygame.MOUSEWHEEL:
                    if pygame.mouse.get_pos()[0] >= RIGHT_X:
                        self.scroll_preview(-ev.y * 3)
                    else:
                        self.move(-ev.y * 3)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    x, y = ev.pos
                    if LEFT_X <= x < LEFT_X + LEFT_W and PANEL_Y + 36 <= y < PANEL_Y + PANEL_H - 8:
                        row = (y - PANEL_Y - 36) // 26
                        chosen = self.scroll + row
                        if chosen < len(self.entries):
                            self.index = chosen
                            self.dirty = True
                            previous, when = self.last_click
                            now = time.monotonic()
                            if previous == (self.cwd, chosen) and now - when < 0.4 and not self.opening:
                                self.activate()
                                self.last_click = (None, 0)
                            else:
                                self.last_click = ((self.cwd, chosen), now)
            if self.dirty:
                self.rebuild_preview()
                self.dirty = False
            if self.opening and time.time() - self.open_t > 0.5:
                self.do_open()
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="File Quest: retro file browser")
    parser.add_argument("folder", nargs="?", help="Starting folder (defaults to home)")
    args = parser.parse_args()
    if args.folder and not os.path.isdir(args.folder):
        parser.error("Starting folder must be an existing directory")
    RetroExplorer(args.folder).run()
