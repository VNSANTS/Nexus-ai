# Nexus Controle 0.1.0

Companion Android do plugin local Nexus. APK Java sem bibliotecas de terceiros, Android 8+ (SDK mínimo 26), compilado para Android 14 (SDK 34). Instalação e ativação são manuais. Não é root nem Device Owner.

## Instalar e parear

1. Abra o APK em Downloads e confirme a instalação pelo Android.
2. Abra **Nexus Controle**. O administrador é opcional: permite somente bloquear a tela.
3. Ative **Nexus — gestos autorizados** em Acessibilidade para início, voltar, recentes, notificações, toque e deslize. Acesso ao conteúdo das janelas não é solicitado.
4. Volte ao app e toque **Iniciar ponte local — 15 minutos**. A notificação permite parar a ponte; a sessão não reinicia sozinha.
5. Toque **Copiar pareamento**. No terminal, execute `nexus control pair`, ou `/control pair` dentro do chat Nexus. O cliente lê o clipboard sem mostrar o segredo à IA. Não cole esse conteúdo em uma mensagem.
6. Execute `nexus control status`. Confira as permissões que o Android informa antes de testar ações.

Se o Android bloquear Acessibilidade de um APK instalado manualmente, consulte Configurações → Apps → Nexus Controle → menu ⋮ → Permitir configurações restritas. A decisão é sua na tela Android. A interface pode variar no XOS. Fonte oficial: https://support.google.com/android/answer/12623953

## Comandos

Use `nexus control help` ou `/control` no Nexus. Exemplos: `nexus control home`, `back`, `recents`, `notifications`, `quick_settings`, `tap X Y`, `swipe X Y X2 Y2 [MS]` e `lock`. Coordenadas são pixels e status informa dimensões. Ações globais retornam aceitação, sem afirmar o resultado visual; gestos retornam confirmação de término ou cancelamento. Não há repetição automática em falhas.

Não implementa leitura da tela, digitação, screenshots, desbloqueio, mudança de senha, apagar dados, instalação silenciosa, controle de outros dispositivos ou execução de shell no Android. O processo da IA continua com suas próprias permissões. Ativar administrador não altera `/root false`.

## Conexão e privacidade

- O usuário inicia cada sessão no app. Servidor apenas em 127.0.0.1:18764, no máximo 15 minutos e 256 comandos. Não há conexão de saída, servidor remoto, boot receiver ou reinício automático.
- Pedidos e respostas autenticados com HMAC-SHA256; segredo não é enviado em headers, URL ou corpo. Sessão aleatória nova em cada início, nonce único e pedidos com validade de 30 segundos impedem reaproveitamento normal de comandos. O cliente não confia em respostas sem assinatura e não usa proxy HTTP.
- O segredo fica nas preferências privadas do app e em config/device-control.json do Nexus, modo 0600. Não entra na biblioteca, no índice, no relatório, no contexto da IA ou na instalação portátil. Cópias anteriores do pareamento ficam somente em state/.private; `nexus control forget` remove ambas. O cliente tenta limpar o clipboard apenas se ainda contiver o pareamento que acabou de consumir.
- O app não lê texto das janelas, contatos, notificações, câmera, áudio, arquivos ou senhas. Não grava comandos, eventos, coordenadas ou transcrições. Permissão INTERNET é necessária para o socket local, que só é aberto como servidor em loopback.
- Acessibilidade permite acionar elementos por coordenadas. Envie somente ações correspondentes ao seu pedido atual. O plugin não amplia autorização para compras, mensagens ou mudanças de conta.
- Para parar, use a notificação/app. Para revogar, use **Revogar pareamentos e parar** no app e `nexus control forget` no terminal. Para desinstalar, desative também o administrador e a Acessibilidade.

## Build verificável

`python build.py` usa aapt2, javac, d8, zipalign e apksigner já instalados. Requer android.jar API 34 no cache interno. SDK obtido de https://dl.google.com/android/repository/platform-34-ext12_r01.zip, tamanho 63559957 e SHA-1 ba80ccbcc29b29f25ac926a08c0b2777f0bce842, conferidos no índice oficial https://dl.google.com/android/repository/repository2-1.xml. Os avisos de APIs antigas são de Device Admin/Display: o build passa para Android 14.

A chave local de assinatura fica somente em .keys/ no armazenamento interno e não acompanha o cartão/instalador portátil. Não a envie a terceiros. Um rebuild em outro aparelho gerará outra assinatura: o Android não aceitará atualizar uma instalação existente com certificado diferente.

Validação realizada: compilação, assinaturas APK v2/v3, manifesto e políticas mínimas, autenticação HMAC Java/Python, rejeição de resposta não autenticada, limites de argumentos, falta de pareamento e permissões de arquivo. **Instalação, ativação e ações reais no Android permanecem pendentes da instalação e autorização do usuário.** Nenhum gesto ou bloqueio foi disparado durante o preparo.

Referências: https://developer.android.com/work/device-admin e https://developer.android.com/reference/android/accessibilityservice/AccessibilityService
