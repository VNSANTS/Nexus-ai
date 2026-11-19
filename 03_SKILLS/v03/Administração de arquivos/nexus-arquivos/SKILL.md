---
name: nexus-arquivos
description: Copiar e verificar arquivos preservando originais.
---

Categoria: Administração de arquivos.
Gatilhos: arquivos backup cópia integridade hash sincronização.

Enumere somente a pasta do projeto. Recuse symlinks que escapem do escopo. Crie destinos exclusivos, use SHA-256 para conferir origem e cópia. Não sobrescreva nem apague originais. Use nexus backup e verify-backup para a biblioteca.

Dependências: Python 3 e comandos efetivamente disponíveis; nenhuma instalação automática.
Ferramentas: nexus context, terminal autorizado e ferramentas locais pertinentes.
Limites: escopo autorizado, sem root, sem segredos, sem apagar dados ou sobrescrever sem backup.
Verificação: registre comando/procedimento, resultado observado, fonte e data; não declare sucesso por inferência.
