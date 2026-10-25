"""Transformações reutilizáveis que podem ser referenciadas nos fluxos JSON."""

TRANSFORMS = {
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "to_float": lambda v: float(v),
    "round2": lambda v: round(float(v), 2),
    "brl": lambda v: f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
}


def apply(name, value):
    if name not in TRANSFORMS:
        raise ValueError(f"Transformação desconhecida: {name}")
    return TRANSFORMS[name](value)
