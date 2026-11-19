# Formato portátil de memória V0.3

Memórias são registros JSON UTF-8 em categorias episódica, semântica, procedural e identidade.
Cada registro guarda título, corpo, origem, data, confiança, estado de validação e evidência.
Informações sem validação ficam pendentes e não entram na busca normal. O índice SQLite/FTS5
é temporário e pode ser reconstruído a partir dos arquivos textuais. Skills são Markdown e
permanecem independentes do modelo.
