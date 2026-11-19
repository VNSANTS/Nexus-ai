---
name: nexus-android
description: Diagnosticar acesso a armazenamento Android sem root.
---

Categoria: Android.
Gatilhos: android armazenamento cartão microsd saf permissões.

Leia /proc/mounts para descobrir volumes. Teste leitura e arquivo novo com nome único. Se acesso direto falhar, consulte termux-saf-dirs e os helps locais. Solicite seletor de pasta somente se necessário. Nunca monte, formate ou amplie permissões para contornar o Android.

Dependências: Python 3 e comandos efetivamente disponíveis; nenhuma instalação automática.
Ferramentas: nexus context, terminal autorizado e ferramentas locais pertinentes.
Limites: escopo autorizado, sem root, sem segredos, sem apagar dados ou sobrescrever sem backup.
Verificação: registre comando/procedimento, resultado observado, fonte e data; não declare sucesso por inferência.
