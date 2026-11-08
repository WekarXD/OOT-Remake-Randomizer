"""Tabla de objetos: actores del remake -> objetos de OoTR."""

# Actor del remake -> objeto de OoTR.
KEY_ITEMS: dict[str, str] = {
    'Item_Sword_Kokiri': 'Kokiri Sword',
    'Item_Range_SlingShot': 'Slingshot',
    'Item_Boomerang': 'Boomerang',
    'Item_Range_Bow': 'Bow',
    'Item_Hookshot': 'Progressive Hookshot',
    'Item_Longshot': 'Progressive Hookshot',
    'Item_Hammer': 'Megaton Hammer',
    'Item_HeavyBoot': 'Iron Boots',
    'Item_HoverBoot': 'Hover Boots',
    'Item_Gauntlet_Silver': 'Progressive Strength Upgrade',
    'Item_Gauntlet_Gold': 'Progressive Strength Upgrade',
    'Item_GlassTruth': 'Lens of Truth',
    'Item_Shield_Mirror': 'Mirror Shield',
    'Item_Arrow_Ice': 'Ice Arrows',
    'Item_BombBag_Small': 'Bomb Bag',
}

# Nivel de los objetos progresivos. El nivel 1 de fuerza (brazalete Goron)
# es fijo, de evento.
ITEM_LEVEL: dict[str, tuple[str, int]] = {
    'Item_Hookshot': ('Progressive Hookshot', 1),
    'Item_Longshot': ('Progressive Hookshot', 2),
    'Item_Gauntlet_Silver': ('Progressive Strength Upgrade', 2),
    'Item_Gauntlet_Gold': ('Progressive Strength Upgrade', 3),
}

LABELS_ES: dict[str, str] = {
    'Item_Sword_Kokiri': 'Espada Kokiri',
    'Item_Range_SlingShot': 'Resortera',
    'Item_Boomerang': 'Bumerán',
    'Item_Range_Bow': 'Arco',
    'Item_Hookshot': 'Gancho',
    'Item_Longshot': 'Gancho largo',
    'Item_Hammer': 'Martillo',
    'Item_HeavyBoot': 'Botas de hierro',
    'Item_HoverBoot': 'Botas levitadoras',
    'Item_Gauntlet_Silver': 'Guanteletes de plata',
    'Item_Gauntlet_Gold': 'Guanteletes de oro',
    'Item_GlassTruth': 'Lente de la Verdad',
    'Item_Shield_Mirror': 'Escudo espejo',
    'Item_Arrow_Ice': 'Flechas de hielo',
    'Item_BombBag_Small': 'Bolsa de bombas',
}

# Actor del remake -> ubicación vanilla de OoTR donde está ese objeto.
KEY_ITEM_HOME: dict[str, str] = {
    'Item_Sword_Kokiri': 'KF Kokiri Sword Chest',
    'Item_Range_SlingShot': 'Deku Tree Slingshot Chest',
    'Item_Boomerang': 'Jabu Jabus Belly Boomerang Chest',
    'Item_Range_Bow': 'Forest Temple Bow Chest',
    'Item_Hookshot': 'Graveyard Dampe Race Hookshot Chest',
    'Item_Longshot': 'Water Temple Longshot Chest',
    'Item_Hammer': 'Fire Temple Megaton Hammer Chest',
    'Item_HeavyBoot': 'Ice Cavern Iron Boots Chest',
    'Item_HoverBoot': 'Shadow Temple Hover Boots Chest',
    'Item_Gauntlet_Silver': 'Spirit Temple Silver Gauntlets Chest',
    'Item_Gauntlet_Gold': 'Ganons Castle Shadow Trial Golden Gauntlets Chest',
    'Item_GlassTruth': 'Bottom of the Well Lens of Truth Chest',
    'Item_Shield_Mirror': 'Spirit Temple Mirror Shield Chest',
    'Item_Arrow_Ice': 'Gerudo Training Ground Maze Path Final Chest',
    'Item_BombBag_Small': 'Dodongos Cavern Bomb Bag Chest',
}

# Objetos de mazmorra (y llaves del minijuego): se quedan siempre vanilla.
DUNGEON_ITEM_PREFIXES = ('Item_Dungeon_', 'Obj_MiniGame_SmallKey', 'Obj_Dungeon_SmallKey_')

# Contenido del remake -> objeto vanilla de OoTR (o familia, ver
# content_matches), para asociar cofres por contenido.
RUPEES: dict[str, str] = {
    'Green': 'Rupee (1)', 'Blue': 'Rupees (5)', 'Red': 'Rupees (20)',
    'Purple': 'Rupees (50)', 'Gold': 'Rupees (200)',
}
DUNGEON_ITEMS: dict[str, str] = {
    'Item_Dungeon_SmallKey': 'Small Key',
    'Item_Dungeon_Map': 'Map',
    'Item_Dungeon_Compass': 'Compass',
    'Item_Dungeon_BossKey': 'Boss Key',
}
FAMILIES: dict[str, str] = {
    'TBox_Shield_Deku': 'Deku Shield',
    'TBox_Shield_Hylian': 'Hylian Shield',
    'Obj_Heart_Piece': 'Piece of Heart',
    'Item_BombchuBundle_Small': 'Bombchus',
    'Item_BombBundle_Small': 'Bombs',
    'TBox_ArrowBundle_Medium': 'Arrows',
    'TBox_ArrowBundle_Large': 'Arrows',
    'TBox_DekuNutBundle': 'Deku Nuts',
    'Item_DekuStickBundle_Small': 'Deku Stick',
    'Obj_MiniGame_SmallKey': 'Small Key (Treasure Chest Game)',
}


def content_matches(drop: str, vanilla: str) -> bool:
    """¿El contenido `drop` del remake equivale al objeto vanilla de OoTR?"""
    if drop in KEY_ITEMS:
        return KEY_ITEMS[drop] == vanilla
    for prefix in ('TBox_Rupee_', 'Obj_Rupee_'):
        if drop.startswith(prefix):
            return RUPEES.get(drop[len(prefix):]) == vanilla
    if drop in DUNGEON_ITEMS:
        return vanilla.startswith(DUNGEON_ITEMS[drop] + ' (')
    fam = FAMILIES.get(drop)
    if fam is None:
        return False
    return vanilla == fam or vanilla.startswith(fam + ' (')
