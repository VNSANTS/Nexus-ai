---
name: nexus-automacao
description: Criar automações locais com falhas recuperáveis.
---

Categoria: Automação.
Gatilhos: automação script rotina idempotência agendamento.

Confirme ferramentas disponíveis. Prefira stdlib e comandos com argumentos estruturados. Implemente exclusão mútua, limites e recuperação de erro. Teste repetição e indisponibilidade de dependências. Não adicione agendamento ou serviço permanente sem necessidade explícita.

Dependências: Python 3 e comandos efetivamente disponíveis; nenhuma instalação automática.
Ferramentas: nexus context, terminal autorizado e ferramentas locais pertinentes.
Limites: escopo autorizado, sem root, sem segredos, sem apagar dados ou sobrescrever sem backup.
Verificação: registre comando/procedimento, resultado observado, fonte e data; não declare sucesso por inferência.
