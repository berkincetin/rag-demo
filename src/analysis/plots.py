"""Ortak grafik stili: Türkçe etiketler, sabit palet, PNG yazıcı.

Notebook'taki her grafik buradan geçer ki dört pazarın rengi her figürde aynı olsun
ve sayılar Türkçe biçimde (binlik nokta, ondalık virgül) yazılsın.
"""

from pathlib import Path

import matplotlib.pyplot as plt

FIGUR_DIZINI = Path("figures")

PAZAR_RENKLERI = {
    "A Pazarı": "#1f77b4",
    "B Pazarı": "#d62728",
    "C Pazarı": "#2ca02c",
    "D Pazarı": "#9467bd",
}

# Şirket 1 analizin öznesi olduğu için vurgulu; rakipler kasıtlı olarak nötr.
SIRKET_RENKLERI = {
    "Şirket 1": "#d62728",
    "Şirket 2": "#7f7f7f",
    "Diğer Şirket": "#c7c7c7",
}


def stil_uygula() -> None:
    """Notebook genelinde geçerli matplotlib ayarlarını kurar."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "figure.figsize": (11, 5),
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def tr_sayi(x: float, ondalik: int = 0) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık ayracı virgül."""
    metin = f"{x:,.{ondalik}f}"
    return metin.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def kaydet(fig, ad: str, dizin: Path = FIGUR_DIZINI) -> Path:
    """Figürü PNG olarak yazar ve yolunu döndürür."""
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    yol = dizin / f"{ad}.png"
    fig.savefig(yol, bbox_inches="tight")
    return yol
