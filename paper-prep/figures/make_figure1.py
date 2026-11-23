"""Figure 1 of the paper, from the repository's stored results.

Left: debt, what pairwise netting leaves, the debt kernel with bank equity
kept, and the Treasury's net debt, with nonbanks in two sectors (Table 2,
columns 2-5). Right: the same with households in five wealth groups
(Section 5); netting is the range over counterparty allocations, from
paper-prep/netting-splits/households-results.json.

From the repository root (needs numpy and scipy for households.py, and matplotlib):
    python3 paper-prep/figures/make_figure1.py figure1.pdf

Writes figure1.pdf and figure1.png. Uses TeX Gyre Pagella if it is installed.
"""
import json, os, subprocess, sys
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager as fm, pyplot as plt

run = lambda p: json.loads(subprocess.check_output([sys.executable, '-I', p, '--json']))
ser = {x['year']: x for x in run('paper-prep/broad-debt/series.py')}
kept = {x['year']: x for x in run('paper-prep/broad-debt/bank_equity_kept.py')}
hr = json.load(open('paper-prep/netting-splits/households-results.json'))
sys.path.insert(0, os.path.abspath('paper-prep/netting-splits'))
import households as hh
pos = lambda x: max(0.0, x)
I = hh.inputs()
Y = sorted(ser)
split = {}
for y in Y:
    gaps = [g['Loans (Liabilities)'] - g['Debt securities'] - g['Loans (Assets)'] for g in I[y]['groups'].values()]
    s = ser[y]
    split[y] = s['tnd'] + sum(pos(g) for g in gaps) + pos(s['gap_d'] + kept[y]['payout'] - sum(gaps)) + pos(s['gap_r'])
    assert abs(kept[y]['debt'] - s['debt']) < 1e-6 and abs(kept[y]['netting'] - s['netting']) < 1e-6
    assert abs(hr[str(y)]['debt'] - s['debt']) < 1e-6

# The paper's figure uses TeX Gyre Pagella (free, from CTAN or a TeX distribution).
# Without it, Matplotlib's default font is used and only the typeface differs.
pagella = [f for f in fm.findSystemFonts() if 'texgyrepagella' in f.lower()]
for f in pagella:
    fm.fontManager.addfont(f)
if not pagella:
    print('note: TeX Gyre Pagella not installed; using the default font', file=sys.stderr)
plt.rcParams.update({'font.size': 9, 'axes.linewidth': 0.6, 'pdf.fonttype': 42})
if pagella:
    plt.rcParams['font.family'] = 'TeX Gyre Pagella'
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e4e3df'
ORANGE, BLUE, AQUA = '#eb6834', '#2a78d6', '#1baf7a'
fig, (a, b) = plt.subplots(1, 2, figsize=(6.4, 3.2), sharey=True)


def frame(ax, title):
    ax.set_xlim(Y[0] - 0.5, Y[-1] + 0.5); ax.set_ylim(0, 100)
    ax.set_xticks([2001, 2010, 2020]); ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK, length=3, width=0.6)
    ax.set_title(title, fontsize=9.5, color=INK, loc='left')


tnd = [ser[y]['tnd'] for y in Y]; debt = [ser[y]['debt'] for y in Y]
a.fill_between(Y, 0, tnd, color=AQUA, alpha=0.28, lw=0, label="Treasury's net debt")
a.plot(Y, debt, color=MUTED, lw=1.5, label='Debt')
a.plot(Y, [ser[y]['netting'] for y in Y], color=ORANGE, lw=1.9, label='Left by netting')
a.plot(Y, [kept[y]['separate'] for y in Y], color=BLUE, lw=2.1, label='Kernel')
frame(a, 'Two nonbank sectors'); a.set_ylabel('USD trillions', color=INK)
lo = [hr[str(y)]['pairwise_most'] for y in Y]; hi = [hr[str(y)]['pairwise_least'] for y in Y]
b.fill_between(Y, 0, tnd, color=AQUA, alpha=0.28, lw=0)
b.plot(Y, debt, color=MUTED, lw=1.5)
b.fill_between(Y, lo, hi, color=ORANGE, alpha=0.22, lw=0, label='Left by netting,\nrange over allocations')
b.plot(Y, lo, color=ORANGE, lw=1.9)
b.plot(Y, hi, color=ORANGE, lw=0.9, ls=(0, (3, 2)))
b.plot(Y, [split[y] for y in Y], color=BLUE, lw=2.1)
frame(b, 'Households in five wealth groups')
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels()
order = ['Debt', 'Left by netting', 'Kernel', "Treasury's net debt"]
a.legend([h1[l1.index(x)] for x in order], order, loc='upper left', frameon=False, fontsize=8, handlelength=1.5)
b.legend(h2, l2, loc='upper left', frameon=False, fontsize=8, handlelength=1.5)
fig.tight_layout(pad=0.05, w_pad=2.1)
out = sys.argv[1]
fig.savefig(out); fig.savefig(out.rsplit('.', 1)[0] + '.png', dpi=200)
