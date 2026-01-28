# backgammon/utils/bitmask.py

def bits_from_indices(indices):
    """Erzeugt eine Maske aus Boardpunkten (1-basiert)."""
    mask = 0
    for i in indices:
        mask |= 1 << i
    return mask


def indices_from_bits(mask: int) -> list[int]:
    """Return list  aus gesetzten Bits."""
    idxs = []
    mask = int(mask)
    while mask:
        lsb = mask & -mask
        idxs.append(lsb.bit_length()-1)  # Bit 0 = Boardpunkt 1
        mask &= mask -1
    return idxs


def set_bit(idx, mask=0):
    """Setzt Bit für Boardpunkt idx (1-basiert)."""
    return mask | (1 << idx)


def clear_bit(idx, mask):
    """Löscht Bit für Boardpunkt idx (1-basiert)."""
    return mask & ~(1 << idx)


def is_bit_set(idx, mask):
    """Prüft, ob Bit für Boardpunkt idx gesetzt ist (1-basiert)."""
    return (mask & (1 << idx)) != 0


def set_all_bits(start, end):
    return ((1 << (end + 1)) - 1) & ~((1 << start) - 1)

def shift_mask(mask, steps):
    """
    Verschiebt alle gesetzten Bits in mask um steps.
    Positive Schritte -> nach links (höhere Boardpunkte),
    negative -> nach rechts (niedrigere Boardpunkte).
    """
    if steps >= 0:
        return mask << steps
    else:
        return mask >> (-steps)

def remove_from_mask(mask, remove):
    """
    Entfernt alle gesetzten Bits von remove aus mask.
    """
    return mask & ~remove

def count_bits(mask: int) -> int:
    """Zählt, wie viele Bits in einer Bitmaske gesetzt sind."""
    return int(bin(mask).count("1"))

def mask_intersection_count(mask1: int, mask2: int) -> int:
    """Zählt die gesetzten Bits im AND zweier Masken."""
    return count_bits(mask1 & mask2)

