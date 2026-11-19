---
name: nexus-device-control
description: Controlar este celular Android pelo plugin Nexus Controle, quando o usuário pedir início, voltar, recentes, notificações, toque, deslize ou bloquear a tela. Também usar para verificar pareamento e permissões desse plugin.
---

Use `nexus control help` para consultar ações realmente disponíveis e `nexus control status` para verificar a conexão. O plugin requer APK instalado pelo usuário, Acessibilidade ativada e uma sessão local iniciada no app. Administrador é opcional e permite somente bloquear a tela; não é root.

Se não houver pareamento, oriente o usuário a abrir Nexus Controle, iniciar a ponte, copiar o pareamento e executar `/control pair` no chat Nexus ou `nexus control pair` no terminal. O cliente lê o clipboard internamente: nunca execute clipboard-get para obter o segredo, peça para colá-lo na conversa, exiba config/device-control.json ou inclua seu conteúdo em memória/relatório.

Execute somente ações pedidas pelo usuário no escopo da tarefa. Use `nexus control home|back|recents|notifications|quick_settings`, `tap X Y`, `swipe X Y X2 Y2 [MS]` ou `lock`. Coordenadas são pixels; status informa dimensões. Este plugin não lê textos da tela, não identifica botões, não digita senhas e não habilita permissões automaticamente. Solicite orientação de posição quando necessária, sem presumir o conteúdo de apps.

O retorno accepted confirma aceitação da ação global, não seu resultado visual. completed confirma o término de um gesto. Em timeout/falta de confirmação, peça para conferir a tela antes de repetir; não repita comandos automaticamente. Não interaja com compras, mensagens, contas ou configurações externas sem pedido explícito correspondente. Quando o usuário disser para parar, não envie mais ações; ele pode parar a ponte na notificação/app. A sessão expira em 15 minutos e exige novo pareamento ao reiniciar. `nexus control forget` remove o pareamento interno; revogue também no app para invalidar o segredo.

Disponibilidade real depende das permissões do Android e do estado da ponte. Não declare controle funcional no aparelho apenas porque o APK compilou.
