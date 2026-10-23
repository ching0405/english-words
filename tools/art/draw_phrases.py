#!/usr/bin/env python3
"""Draw the seven phrase scenes (images/phrases/<name>.svg), style: STYLE_GUIDE.md.

Every phrase is said to someone, so each scene has two people with faces that
show the feeling. The same child (blue top, brown hair) appears in every
scene, so a child can follow "that's me"; a friend (pink top, pigtails) and a
grown-up (purple top, bun) are the other person. Scenes that could look alike
are kept apart by their key action:
  Hello      friend arrives at the open front door, both wave
  Goodbye    the child rides away in a car, waving out of the window
  Thank you  a gift passes between the two, a heart above
  Please     palms pressed together, looking up at the grown-up's apple
  Sorry      worried face, hand on head, a knocked-over block tower, friend sad
  Ready      backpack on, thumbs up, a big tick; the grown-up is pleased
  Your name  a question bubble (person + ?) toward a friend with a name badge

Usage: python3 tools/art/draw_phrases.py
"""
from draw_words import shape, line, fill, hl, clipped, P, INK, ROOT

OUT = ROOT / 'images/phrases'
SKIN = P['tan']
WHO = {  # top colour, hair colour, hair style, height scale
    'me': (P['blue'], P['dark_brown'], 'tuft', .98),
    'friend': (P['pink'], P['orange'], 'pigtails', .94),
    'adult': (P['purple'], P['brown'], 'bun', 1.1),
}


def g(x, y, s, *inner, rot=0):
    return f'<g transform="translate({x} {y}) rotate({rot}) scale({s})">{"".join(inner)}</g>'


def hand(x, y):
    return shape('circle', SKIN, shade=False, line=6, cx=x, cy=y, r=15)


def arm(x0, y0, x1, y1, bend=None):
    """Arm from the shoulder to a hand; `bend` is an elbow point."""
    d = f'M{x0} {y0}' + (f'L{bend[0]} {bend[1]}' if bend else '') + f'L{x1} {y1}'
    return line(d, 22) + hand(x1, y1)


def thumb_up(x, y):
    return (shape('rect', SKIN, shade=False, line=6, x=x - 7, y=y - 36, width=14, height=30, rx=7)
            + shape('rect', SKIN, shade=False, line=6, x=x - 17, y=y - 12, width=34, height=28, rx=10))


def hair(style, color):
    cap = 'M-70 -230a70 70 0 0 1 140 0q-20-26-52-24q-18-16-36-6q-30-4-52 30z'
    out = ''
    if style == 'pigtails':
        out += shape('circle', color, cx=-78, cy=-238, r=22) + shape('circle', color, cx=78, cy=-238, r=22)
    if style == 'bun':
        out += shape('circle', color, cx=0, cy=-300, r=26)
    out += shape('path', color, d=cap)
    if style == 'tuft':
        out += line('M-6 -292q10-26 26-20', 10, INK)
    return out


def face(mood):
    """Eyes, cheeks and mouth on a head centred at (0, -225)."""
    out = ''
    ey = -214 if mood not in ('hope',) else -222
    for x in (-25, 25):
        out += fill('ellipse', INK, cx=x, cy=ey, rx=9, ry=12) + fill('circle', '#fff', cx=x + 3, cy=ey - 5, r=3.5)
        out += fill('ellipse', P['blush'], cx=x * 1.75, cy=-190, rx=13, ry=8, opacity=.65)
    if mood == 'smile':
        out += line('M-18 -190q18 16 36 0', 7)
    elif mood == 'open':   # happy, talking
        out += shape('path', P['red'], shade=False, line=6, d='M-22 -194q22 30 44 0z')
    elif mood == 'hope':
        out += line('M-30 -250l14-6M30 -250l-14-6', 6) + shape('ellipse', P['red'], shade=False, line=6, cx=0, cy=-188, rx=10, ry=12)
    elif mood == 'sorry':  # brows up in the middle, small wobbly mouth
        out += line('M-38 -234l22-8M38 -234l-22-8', 6) + line('M-16 -184q8-10 16-4q8 6 16-4', 6)
    elif mood == 'sad':
        out += line('M-38 -234l22-8M38 -234l-22-8', 6) + line('M-16 -182q16-14 32 0', 7)
        out += shape('path', P['sky'], shade=False, line=5, d='M-40 -198q-8 14 0 20q8-6 0-20z')
    return out


def person(who, x, y, mood='smile', arms='', front='', back='', tilt=0):
    """A person standing with feet at (x, y). `arms` are drawn over the body,
    `front` over everything, `back` behind it (local coordinates: head at
    (0, -225), shoulders at (+-58, -132), feet at 0)."""
    top, hair_color, style, s = WHO[who]
    body = (line('M-28 -40v32M28 -40v32', 20)
            + shape('rect', top, x=-70, y=-170, width=140, height=136, rx=52))
    head = g(0, -150, 1, shape('circle', SKIN, cx=0, cy=-75, r=70)
             + g(0, 150, 1, hair(style, hair_color), face(mood)) + hl(-30, -112, 18, 10, -25), rot=tilt)
    return g(x, y, s, back, body, head, arms, front)


def ground(cx=256, rx=215):
    return fill('ellipse', INK, cx=cx, cy=456, rx=rx, ry=16, opacity=.12)


def heart(x, y, s=1):
    return g(x, y, s, shape('path', P['red'], d='M0 18c-26-16-30-32-20-40 8-6 16-2 20 6 4-8 12-12 20-6 10 8 6 24-20 40z'))


def gift(x, y):
    return (shape('rect', P['yellow'], x=x - 40, y=y - 34, width=80, height=64, rx=10)
            + line(f'M{x} {y - 34}v64M{x - 40} {y - 4}h80', 9, P['red'])
            + line(f'M{x} {y - 34}c-28-26-34 2 0 0c28-26 34 2 0 0', 8, P['red']))


def apple(x, y, r=30):
    return (shape('circle', P['red'], cx=x, cy=y, r=r) + line(f'M{x} {y - r}l6-16', 8, P['dark_brown'])
            + shape('ellipse', P['green'], shade=False, line=5, cx=x + 18, cy=y - r - 8, rx=13, ry=7))


def scene_hello():
    door = (shape('rect', P['cream'], x=40, y=88, width=150, height=360, rx=14)
            + shape('path', P['blue'], d='M42 92l-24 12v338l24 6z')
            + fill('rect', P['sky'], x=60, y=110, width=110, height=318, rx=8, opacity=.5)
            + line('M40 88h150', 8))
    sun = shape('circle', P['yellow'], cx=446, cy=72, r=34) + line('M446 22v-8M492 72h8M478 38l6-6M478 106l6 6', 7, P['orange'])
    wave = lambda x: line(f'M{x - 26} -262q-10-20 4-38M{x + 26} -262q10-20-4-38', 6, P['orange'])
    me = person('me', 140, 446, 'open', arms=arm(-58, -132, -76, -60) + arm(58, -132, 96, -250, bend=(100, -160)) + wave(96))
    friend = person('friend', 392, 446, 'open', arms=arm(58, -132, 74, -60) + arm(-58, -132, -96, -250, bend=(-100, -160)) + wave(-96),
                    back=shape('rect', P['green'], x=56, y=-150, width=46, height=60, rx=10))
    return door + sun + ground(260, 200) + me + friend


def scene_goodbye():
    friend = person('friend', 110, 446, 'smile', arms=arm(-58, -132, -70, -58) + arm(58, -132, 100, -262, bend=(104, -180))
                    + line('M74 -290q-10-20 4-38M126 -290q10-20-4-38', 6, P['orange']))
    car = shape('path', P['orange'], d='M178 412v-66q0-18 18-20l48-6 44-82q10-18 30-18h108q22 0 32 20l34 80q34 6 34 36v56z')
    window = 'M300 318l32-74h96l30 74z'
    head = g(380, 432, .62, shape('circle', SKIN, cx=0, cy=-225, r=70), hair('tuft', P['dark_brown']), face('open'))
    me = shape('path', P['sky'], line=0, d=window) + clipped('path', {'d': window}, head) + line(window, 8)
    wave = arm(440, 300, 482, 196, bend=(470, 262)) + line('M464 170q-8-20 6-34M506 176q8-20-6-34', 6, P['orange'])
    wheels = ''.join(shape('circle', P['tyre'], cx=x, cy=414, r=34) + fill('circle', P['gray'], cx=x, cy=414, r=12) for x in (258, 420))
    # The car (child inside, waving) drives off to the right.
    return ground(270, 240) + friend + g(34, 60, .86, car, me, wave, wheels)


def scene_thank_you():
    friend = person('friend', 128, 446, 'smile', arms=arm(58, -132, 124, -112, bend=(98, -96)) + arm(-58, -132, -70, -60))
    me = person('me', 384, 446, 'open', arms=arm(-58, -132, -120, -112, bend=(-96, -96)) + arm(58, -132, 70, -60))
    return ground() + friend + me + gift(256, 362) + heart(256, 70, 1.5) + heart(206, 112, .8) + heart(306, 108, .8)


def scene_please():
    adult = person('adult', 370, 446, 'smile', arms=arm(-58, -132, -70, -50) + arm(58, -132, 84, -252, bend=(108, -180)),
                   front=apple(92, -296, 36))
    palms = ''.join(shape('ellipse', SKIN, shade=False, line=6, cx=x, cy=-150, rx=15, ry=36) for x in (-11, 11))
    hands = line('M-58 -132L-30 -100L-14 -120M58 -132L30 -100L14 -120', 22) + palms
    me = person('me', 140, 446, 'hope', arms=hands, tilt=-8)
    return ground() + adult + me


def scene_sorry():
    blocks = (shape('rect', P['yellow'], x=196, y=392, width=52, height=52, rx=8, transform='rotate(-14 222 418)')
              + shape('rect', P['green'], x=250, y=402, width=48, height=48, rx=8, transform='rotate(18 274 426)')
              + shape('rect', P['red'], x=228, y=354, width=44, height=44, rx=8, transform='rotate(40 250 376)')
              + shape('rect', P['blue'], x=300, y=414, width=40, height=34, rx=8))
    friend = person('friend', 116, 446, 'sad', arms=arm(-58, -132, -70, -56) + arm(58, -132, 72, -56))
    me = person('me', 392, 446, 'sorry', tilt=10,
                arms=arm(58, -132, 40, -264, bend=(104, -210)) + arm(-58, -132, -132, -86, bend=(-104, -120)))
    return ground() + friend + me + blocks


def scene_ready():
    bag = shape('rect', P['green'], x=-92, y=-176, width=50, height=110, rx=16)
    straps = line('M-44 -164q20 40 6 96M44 -164q-20 40-6 96', 12, P['green'])
    me = person('me', 330, 446, 'open', back=bag,
                arms=straps + arm(-58, -132, -84, -56) + line('M58 -132L112 -176', 22) + g(118, -182, 1.4, thumb_up(0, 0)))
    adult = person('adult', 120, 446, 'smile', arms=arm(-58, -132, -42, -70, bend=(-84, -96)) + arm(58, -132, 42, -70, bend=(84, -96)))
    tick = shape('circle', P['green'], cx=444, cy=86, r=46) + line('M422 86l16 16 28-32', 12, P['white'])
    return ground() + adult + me + tick


def scene_your_name():
    me = person('me', 136, 446, 'open', arms=arm(-58, -132, -70, -56) + arm(58, -132, 130, -150, bend=(100, -110)))
    badge = shape('rect', P['white'], line=6, x=-34, y=-130, width=68, height=44, rx=8) + line('M-18 -112h36M-18 -100h22', 5, P['gray'])
    friend = person('friend', 384, 446, 'smile', arms=arm(-58, -132, -70, -56) + arm(58, -132, 70, -56), front=badge)
    bubble = (shape('path', P['white'], d='M150 44h180q24 0 24 24v76q0 24-24 24h-110l-40 34 8-34h-38q-24 0-24-24v-76q0-24 24-24z')
              + shape('circle', P['pink'], shade=False, line=6, cx=208, cy=86, r=22)
              + shape('path', P['pink'], shade=False, line=6, d='M172 150q0-36 36-36t36 36z')
              + line('M280 82q0-22 22-22t22 22q0 16-22 22v14', 11, P['purple']) + fill('circle', P['purple'], cx=302, cy=144, r=7))
    return ground() + me + friend + bubble


SCENES = {'thank_you': scene_thank_you, 'goodbye': scene_goodbye, 'your_name': scene_your_name,
          'ready': scene_ready, 'hello': scene_hello, 'sorry': scene_sorry, 'please': scene_please}

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in SCENES.items():
        (OUT / f'{name}.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">' + draw() + '</svg>')
    print(f'wrote {len(SCENES)} scenes to {OUT.relative_to(ROOT)}')
