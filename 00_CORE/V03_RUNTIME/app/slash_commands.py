"""Direct slash commands implemented by Nexus, without an intermediary CLI prefix."""
from dataclasses import replace
import time
import nexus as memory

DEFAULT_USER_NAME = 'Você'

def load_user_name():
    value=memory.load(memory.BASE/'config/user.json',{})
    name=value.get('name') if isinstance(value,dict) else None
    if isinstance(name,str) and 0<len(name)<=40 and name==name.strip() and all(c.isprintable() for c in name):return name
    return DEFAULT_USER_NAME

ALIASES = {'/help':'/ajuda', '/exit':'/sair', '/quit':'/sair', '/new':'/novo',
    '/clear':'/novo', '/reset':'/novo', '/voice':'/voz', '/memories':'/memory',
    '/settings':'/config', '/debug-config':'/config', '/allowed-tools':'/permissions',
    '/sandbox':'/permissions', '/code-review':'/review', '/cost':'/usage', '/stats':'/usage',
    '/branch':'/fork', '/cwd':'/pwd', '/bashes':'/tasks', '/ps':'/tasks',
    '/subagents':'/agents', '/list-agents':'/agents', '/peers':'/agents', '/checkup':'/doctor','/admin':'/control'}

ENTRIES = (
    ('/control','Controle do celular: pareamento, status e ações'),
    ('/control open','Abrir o app Nexus Controle'),
    ('/control pair','Parear pelo botão Copiar pareamento do app'),
    ('/control status','Conferir conexão e permissões reais'),
    ('/control home','Ir à tela inicial do Android'),
    ('/control back','Voltar no Android'),
    ('/control recents','Abrir aplicativos recentes'),
    ('/control notifications','Abrir notificações, sem ler conteúdo'),
    ('/control quick_settings','Abrir ajustes rápidos'),
    ('/control tap','Tocar: pedir coordenadas em pixels'),
    ('/control swipe','Deslizar: pedir coordenadas em pixels'),
    ('/control lock','Bloquear tela; requer administrador ativo'),
    ('/control forget','Remover o pareamento interno'),
    ('/control apk','Ver onde está o APK para instalação'),
    ('/model','Escolher modelo aqui no Nexus'),
    ('/effort','Escolher o nível de raciocínio'),
    ('/plan','Ativar planejamento com ferramentas só de leitura'),
    ('/compact','Compactar a conversa atual pelo Codex'),
    ('/context','Ver contexto e último uso de tokens'),
    ('/memory','Consultar memória e instruções do Nexus'),
    ('/permissions','Ver ou restringir permissões da sessão'),
    ('/config','Ver preferências locais da sessão'),
    ('/usage','Consultar limites retornados pelo Codex'),
    ('/diff','Mostrar git diff do workspace'),
    ('/review','Pedir revisão sem permitir alterações'),
    ('/security-review','Pedir revisão defensiva sem alterações'),
    ('/doctor','Diagnosticar a integração Nexus/Codex'),
    ('/mcp','Listar servidores MCP da conexão atual'),
    ('/plugins','Listar plugins pelo Codex instalado'),
    ('/plugin','Listar plugins pelo Codex instalado'),
    ('/reload-skills','Atualizar as cópias revisadas das skills'),
    ('/fork','Indisponível: conversa efêmera sem histórico salvo'),
    ('/rename','Dar um nome local à conversa'),
    ('/copy','Copiar a última resposta ao clipboard'),
    ('/init','Ver as instruções já preparadas do Nexus'),
    ('/tasks','Ver estado da conexão e da tarefa atual'),
    ('/agents','Ver agente principal e roteador'),
    ('/pwd','Ver a pasta do terminal !'),
    ('/cd','Trocar a pasta do terminal !'),
    ('/terminal-setup','Ver os atalhos do terminal Nexus'),
    ('/keymap','Ver os atalhos do terminal Nexus'),
    ('/warnings','Ver avisos técnicos recentes'),
)


def handle(chat, name, arg, say):
    if name == '/control':
        import shlex
        from device_control import run
        arguments=shlex.split(arg) if arg else ['help']
        if arguments in [['tap'],['swipe']]:
            text=input('Coordenadas '+('X Y' if arguments[0]=='tap' else 'X Y X2 Y2 [MS]')+'; Enter cancela › ').strip()
            if not text:return True
            arguments+=shlex.split(text)
        memory.out(run(memory.BASE,arguments))
    elif name == '/model':
        chat.connect(); names = list(chat.router.catalog)
        say('Modelo: '+(chat.model_override or 'auto (roteador)'))
        if not arg:
            say('0 · auto (roteador)')
            for index, model in enumerate(names, 1): say(str(index)+' · '+model)
            arg = input('Modelo: número ou nome; Enter mantém › ').strip()
            if not arg:return True
        if arg in {'auto','0'}: chat.model_override = None
        else:
            if arg.isdigit() and 1 <= int(arg) <= len(names): arg = names[int(arg)-1]
            if arg not in chat.router.catalog:raise ValueError('Modelo ausente do catálogo disponível nesta conta')
            chat.model_override = arg
        say('Modelo selecionado: '+(chat.model_override or 'auto'),'green')
    elif name == '/effort':
        if not arg:
            say('Atual: '+(chat.effort_override or 'auto'))
            arg=input('Raciocínio: auto, low, medium ou high; Enter mantém › ').strip()
            if not arg:return True
        if arg not in {'auto','low','medium','high'}:raise ValueError('Use auto, low, medium ou high')
        chat.effort_override = None if arg=='auto' else arg;say('Raciocínio: '+arg,'green')
    elif name == '/plan':
        if arg in {'off','on'}:chat.plan_mode=arg=='on'
        elif not arg:chat.plan_mode=not chat.plan_mode
        else:chat.plan_mode=True
        say('Planejamento '+('ativado: ferramentas em somente leitura.' if chat.plan_mode else 'desativado.'),'green')
        if arg and arg not in {'off','on'}:chat.ask(arg)
    elif name == '/permissions':
        if not arg:arg=input('Permissões: read-only ou workspace-write; Enter consulta › ').strip()
        if arg:
            if arg not in {'read-only','workspace-write'}:raise ValueError('Nesta interface: read-only ou workspace-write')
            chat.permission_mode=arg
        roots=[str(memory.BASE)]+([str(memory.library())] if memory.library() else [])
        memory.out({'sandbox':chat.permission_mode,'plan_read_only':chat.plan_mode,'approvalPolicy':'on-request',
                    'writable_roots':[] if chat.permission_mode=='read-only' or chat.plan_mode else roots})
    elif name == '/compact':
        if arg:raise ValueError('/compact compacta a conversa atual; instruções de resumo não suportadas pelo protocolo instalado')
        chat.connect();chat.compaction_pending=True;chat.compaction_error=None
        try:
            chat.rpc.call('thread/compact/start',{'threadId':chat.thread})
            say('Compactação solicitada ao Codex; aguardando confirmação…','dim')
            deadline=time.monotonic()+90
            while chat.compaction_pending:
                if time.monotonic()>deadline:raise ValueError('Compactação ainda sem confirmação; não declarada concluída')
                chat.rpc.pump(timeout=.5)
            if chat.compaction_error:raise ValueError(chat.compaction_error)
            say('Compactação confirmada pelo Codex. Memórias no cartão preservadas.','green')
        finally:chat.compaction_pending=False
    elif name == '/context':
        memory.out(memory.context(arg,compact=True) if arg else {'last_request':chat.timings,'token_usage':chat.token_usage,
                   'note':'Tokens só aparecem se o Codex enviar a notificação; nenhuma porcentagem estimada.'})
    elif name == '/memory':
        if arg:memory.out(memory.context(arg,compact=True))
        else:memory.out({'library':memory.config()['path'],'instructions':str(memory.BASE/'workspace/AGENTS.md'),
                        'record':'/lembrar TEXTO','search':'/buscar TERMOS','working_memory':memory.work()})
    elif name == '/config':memory.out({'model':chat.model_override or 'auto','effort':chat.effort_override or 'auto',
        'plan':chat.plan_mode,'sandbox':chat.permission_mode,'scope':'somente esta sessão; sem credenciais ou configuração global'})
    elif name == '/usage':
        chat.connect();memory.out(chat.rpc.call('account/rateLimits/read',{}))
        say('São limites informados pelo servidor; custo monetário desta sessão não calculado.','dim')
    elif name == '/mcp':
        chat.connect();memory.out(chat.rpc.call('mcpServerStatus/list',{}))
    elif name in {'/plugin','/plugins'}:
        if arg:raise ValueError('Este menu lista plugins; alterações não foram implementadas aqui')
        import json
        for path in (memory.BASE/'plugins').glob('*/plugin.json'):
            item=json.loads(path.read_text());memory.out({'nexus_plugin':item['id'],'version':item['version'],'command':item['command'],'requires_android_activation':item.get('manual_android_activation_required',False)})
        chat.actions.native('codex','plugin list',memory.BASE,[])
    elif name == '/reload-skills':
        with memory.lock():memory.out(memory.refresh_skills())
    elif name == '/diff':
        if arg:raise ValueError('/diff mostra somente o workspace Nexus')
        code=chat.actions.native_git_diff(memory.BASE/'workspace')
        if code:raise ValueError('git diff falhou; o workspace precisa ser um repositório Git')
    elif name in {'/review','/security-review'}:
        prompt=('Revise defensivamente a segurança das alterações deste workspace' if name=='/security-review' else 'Revise a correção das alterações deste workspace')
        if arg:prompt+='; foco solicitado: '+arg
        prompt+='. Apenas relate achados verificáveis. Não altere arquivos, não publique comentários e não use outros agentes.'
        previous=chat.readonly_request;chat.readonly_request=True
        try:chat.ask(prompt)
        finally:chat.readonly_request=previous
    elif name == '/doctor':
        if arg:raise ValueError('/doctor verifica a integração local sem alterar a instalação')
        from terminal_ui import doctor
        doctor()
    elif name == '/fork':
        say('Indisponível: o Codex instalado exige histórico salvo para /fork. O Nexus usa conversa efêmera e não salva transcrições. Nenhuma ramificação criada.','yellow')
    elif name == '/rename':
        if not arg:arg=input('Nome da conversa › ').strip()
        if not arg:raise ValueError('Informe um nome')
        chat.session_name=''.join(c for c in arg if c.isprintable())[:100]
        say('Conversa: '+chat.session_name,'green')
    elif name == '/user':
        if arg.lower()=='reset':
            chat.user_name=DEFAULT_USER_NAME
        else:
            if not arg:
                say('Nome atual: '+chat.user_name,'dim')
                arg=input('Nome que aparece ao lado de NEXUS - AI; Enter cancela › ').strip()
                if not arg:return True
            name=' '.join(arg.split())
            if not name or len(name)>40 or any(not c.isprintable() for c in name):
                raise ValueError('Use um nome de até 40 caracteres imprimíveis')
            chat.user_name=name
        memory.save(memory.BASE/'config/user.json',{'name':chat.user_name})
        say('Nome exibido: '+chat.user_name,'green')
    elif name == '/copy':
        if not chat.last_answer:raise ValueError('Nenhuma resposta para copiar')
        from terminal_ui import run_android
        run_android(['termux-clipboard-set',chat.last_answer],timeout=10);say('Última resposta copiada.','green')
    elif name == '/init':
        say('Nexus já preparado: '+str(memory.BASE/'workspace/AGENTS.md')+'. Arquivo existente preservado.')
    elif name == '/tasks':memory.out({'connection':chat.connection_state(),'turn_active':bool(chat.turn),'background_tasks':[],
            'note':'O Nexus não gerencia tarefas de terminal em background nesta versão.'})
    elif name == '/agents':memory.out({'principal':chat.model_override or 'auto','roteador':chat.last_route,
            'delegation':'Nenhum agente adicional criado por este comando.'})
    elif name == '/pwd':say(str(chat.actions.cwd))
    elif name == '/cd':
        import shlex
        if not arg:arg=input('Pasta do terminal ! › ').strip()
        if not arg:return True
        chat.actions.shell('cd '+shlex.quote(arg));say(str(chat.actions.cwd))
        say('A pasta das ferramentas da IA continua sendo o workspace Nexus.','dim')
    elif name in {'/terminal-setup','/keymap'}:say('↑↓ selecionam · Tab completa · Enter executa · Esc fecha · Ctrl+C interrompe · ! executa no terminal.')
    elif name == '/warnings':memory.out({'connection_warning':chat.warm_error,'server':list(getattr(chat.rpc,'errors',[]))})
    else:return False
    return True


def apply_preferences(chat, plan):
    if chat.model_override:
        model=chat.model_override
        modes=chat.router.catalog[model].get('inputModalities',['text','image'])
        if chat.attachments and 'image' not in modes:raise ValueError('Modelo selecionado não aceita imagens; use /model para trocar')
        plan=replace(plan,model=model,source='seleção manual',reason='Modelo escolhido em /model.')
    if chat.effort_override:plan=replace(plan,effort=chat.effort_override)
    supported=chat.router.catalog.get(plan.model,{}).get('supportedReasoningEfforts',[])
    levels=[e.get('reasoningEffort') for e in supported]
    if levels and plan.effort not in levels:raise ValueError('Raciocínio não suportado pelo modelo: '+', '.join(levels))
    return plan
