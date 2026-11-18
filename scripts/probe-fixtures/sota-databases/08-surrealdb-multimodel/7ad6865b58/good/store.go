package store

// near miss: the same cast with the nullable parameter defaulted
const upsertTags = `UPDATE indicator SET tags = <array<string>> ($tags ?? []) WHERE id = $id`
