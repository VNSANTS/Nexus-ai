---
name: nexus-defesa
description: Revisar exposição e permissões de sistemas autorizados.
---

Categoria: Cibersegurança defensiva.
Gatilhos: segurança defensiva auditoria vulnerabilidade permissões.

Delimite o sistema autorizado. Faça inventário somente de leitura e busque configuração insegura sem imprimir segredos. Proponha correção reversível com backup e valide no escopo. Sem exploração externa, varredura de terceiros ou desativação de controles.

Dependências: Python 3 e comandos efetivamente disponíveis; nenhuma instalação automática.
Ferramentas: nexus context, terminal autorizado e ferramentas locais pertinentes.
Limites: escopo autorizado, sem root, sem segredos, sem apagar dados ou sobrescrever sem backup.
Verificação: registre comando/procedimento, resultado observado, fonte e data; não declare sucesso por inferência.
