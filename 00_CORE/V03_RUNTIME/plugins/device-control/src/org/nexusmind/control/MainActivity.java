package org.nexusmind.control;

import android.Manifest;
import android.app.Activity;
import android.app.admin.DevicePolicyManager;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Bundle;
import android.os.PersistableBundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.security.SecureRandom;
import org.json.JSONObject;

public final class MainActivity extends Activity {
    TextView status;
    static String randomHex(int count) { byte[] bytes=new byte[count];new SecureRandom().nextBytes(bytes);StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return s.toString(); }
    static synchronized String token(android.content.Context c) {
        android.content.SharedPreferences p=c.getSharedPreferences("bridge",MODE_PRIVATE);
        String token=p.getString("token",null);
        if(token==null) { token=randomHex(32);p.edit().putString("token",token).commit(); }
        return token;
    }
    void add(LinearLayout layout,String title,android.view.View.OnClickListener click){Button button=new Button(this);button.setText(title);button.setOnClickListener(click);layout.addView(button);}
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(28,28,28,28);scroll.addView(layout);setContentView(scroll);
        TextView title=new TextView(this);title.setText("NEXUS CONTROLE\nControle local autorizado");title.setTextSize(23);layout.addView(title);
        TextView description=new TextView(this);description.setText("Administrador: apenas bloquear a tela.\nAcessibilidade: início, voltar, recentes, notificações, toque e deslize.\nNão lê textos ou senhas, não apaga dados e não concede root.\nA ponte só aceita conexões do próprio aparelho com pareamento secreto; expira em 15 minutos.\n");layout.addView(description);
        status=new TextView(this);layout.addView(status);
        add(layout,"1. Ativar administrador (opcional: bloquear tela)",v->{Intent i=new Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN);i.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN,new ComponentName(this,AdminReceiver.class));i.putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION,"Permite somente bloquear a tela por comando seu. Sem apagar dados ou trocar senha.");startActivity(i);});
        add(layout,"2. Abrir Acessibilidade do Android",v->startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        add(layout,"3. Iniciar ponte local — 15 minutos",v->{if(android.os.Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},11);startForegroundService(new Intent(this,BridgeService.class));status.postDelayed(()->refresh(),500);});
        add(layout,"4. Copiar pareamento para usar no Nexus",v->{try {if(BridgeService.until<=android.os.SystemClock.elapsedRealtime()){status.setText("Inicie a ponte antes de copiar o pareamento.");return;}JSONObject config=new JSONObject();config.put("service","nexus-device-control");config.put("protocol",1);config.put("port",BridgeService.PORT);config.put("session",BridgeService.session);config.put("token",token(this));ClipData clip=ClipData.newPlainText("Pareamento privado Nexus",config.toString());if(android.os.Build.VERSION.SDK_INT>=33){PersistableBundle extras=new PersistableBundle();extras.putBoolean("android.content.extra.IS_SENSITIVE",true);clip.getDescription().setExtras(extras);}((ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(clip);status.setText("Pareamento copiado. No terminal use /control pair. Não envie o conteúdo à IA ou a outras pessoas.");} catch(Exception ignored){status.setText("Falha ao copiar pareamento");}});
        add(layout,"Parar ponte local",v->{stopService(new Intent(this,BridgeService.class));refresh();});
        add(layout,"Revogar pareamentos e parar",v->{stopService(new Intent(this,BridgeService.class));getSharedPreferences("bridge",MODE_PRIVATE).edit().remove("token").commit();token(this);refresh();});
        add(layout,"Desativar administrador Nexus",v->{((DevicePolicyManager)getSystemService(DEVICE_POLICY_SERVICE)).removeActiveAdmin(new ComponentName(this,AdminReceiver.class));refresh();});
        TextView help=new TextView(this);help.setText("\nInstalação por APK: se o Android bloquear a Acessibilidade, abra Configurações → Apps → Nexus Controle → menu ⋮ → Permitir configurações restritas, somente se confiar neste APK. Depois volte à Acessibilidade.\nPara remover: pare a ponte, desative Acessibilidade e administrador, então desinstale normalmente.");layout.addView(help);
    }
    @Override public void onResume(){super.onResume();refresh();}
    void refresh(){if(status!=null)status.setText(ControlAccessibility.status(this).toString());}
}
