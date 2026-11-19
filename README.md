# NEXUS - AI (portátil)

Camada de memória persistente e chat em terminal usando o Codex CLI app-server como executor. O Nexus não treina modelo: identidade, memórias, conhecimento e skills ficam em arquivos reutilizáveis; o índice SQLite FTS5 é um cache local reconstruível.

## Instalação no Kali Linux

Requisitos: Python 3.10+ com SQLite FTS5, Git e Codex CLI já instalado e autenticado no aparelho de destino. Este projeto não instala o Codex, não transfere login, não pede chave de provedor e não instala pacotes do sistema. Use uma instalação persistente do Kali; alterações numa sessão live sem persistência podem desaparecer ao reiniciar.

```sh
git clone https://github.com/VNSANTS/Nexus-ai.git ~/NEXUS_MIND
cd ~/NEXUS_MIND
python3 00_CORE/V03_RUNTIME/app/install_portable.py --library "$PWD"
export PATH="$HOME/.local/bin:$PATH"
nexus sync
nexus doctor
nexus
```

O instalador cria `~/nexus-mind` e `~/.local/bin/nexus`, recusa sobrescrever destinos existentes, verifica runtime e skills por SHA-256 e inicia o estado de root como `unable`. Se `~/.local/bin` não estiver no PATH, adicione-o ao perfil do seu shell. Consulte `nexus --help` para os comandos.

## Dados e privacidade

- `00_CORE/`: identidade, regras e runtime portátil.
- `01_MEMORY/v03/`: memórias específicas do usuário; ignoradas pelo Git.
- `02_KNOWLEDGE/`: documentos locais; revise antes de publicar.
- `03_SKILLS/`: skills do Nexus e a coleção importada VNSANTS. As importadas ficam marcadas como não confiáveis até revisão.
- Cache SQLite, estado, configuração privada, backups e relatórios não fazem parte do Git.

Este repositório não contém histórico de conversas. Não publique transcrições, credenciais, pareamentos do dispositivo, relatórios locais ou backups. O `.gitignore` exclui dados locais conhecidos; confira `git status` antes de qualquer envio manual.

## Limites de plataforma

O mecanismo de memória usa a biblioteca padrão do Python e tem como alvo Linux POSIX. O chat requer o Codex app-server já disponível. O Kali ainda precisa ser testado no dispositivo físico. Voz, seletor de fotos, SAF e controle de aparelho Android dependem de Android/Termux e não funcionam num Kali comum. O código-fonte do companion Android está incluído, mas APK, assinatura, chaves e pareamento foram excluídos.

Os testes usam fixtures temporárias e não chamam modelos. Rode: `python3 -m unittest discover -s 00_CORE/V03_RUNTIME/tests -p 'test_*.py'`.
