package store

const upsertTags = `UPDATE indicator SET tags = <array<string>> $tags WHERE id = $id`
