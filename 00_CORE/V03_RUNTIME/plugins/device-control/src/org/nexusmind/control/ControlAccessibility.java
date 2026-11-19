package org.nexusmind.control;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.app.admin.DevicePolicyManager;
import android.content.ComponentName;
import android.content.Context;
import android.graphics.Path;
import android.view.accessibility.AccessibilityEvent;
import org.json.JSONObject;

public final class ControlAccessibility extends AccessibilityService {
    static volatile ControlAccessibility instance;
    public interface Reply { void done(JSONObject value); }
    @Override public void onServiceConnected() { instance=this; }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { /* No event data is read or retained. */ }
    @Override public void onInterrupt() {}
    @Override public void onDestroy() { if(instance==this)instance=null; super.onDestroy(); }

    static JSONObject result(boolean ok, String key, Object value) {
        JSONObject r=new JSONObject();try { r.put("ok",ok);r.put(key,value); } catch(Exception ignored) {}return r;
    }
    static boolean admin(Context context) {
        return ((DevicePolicyManager)context.getSystemService(Context.DEVICE_POLICY_SERVICE)).isAdminActive(new ComponentName(context,AdminReceiver.class));
    }
    static JSONObject status(Context context) {
        JSONObject r=result(true,"accessibility",instance!=null);
        try { android.util.DisplayMetrics m=metrics(context);r.put("width",m.widthPixels);r.put("height",m.heightPixels);r.put("admin",admin(context));r.put("screen_content_reading",false);r.put("session_remaining_seconds",Math.max(0,(BridgeService.until-android.os.SystemClock.elapsedRealtime())/1000)); } catch(Exception ignored) {}
        return r;
    }
    static android.util.DisplayMetrics metrics(Context context){android.util.DisplayMetrics m=new android.util.DisplayMetrics();((android.view.WindowManager)context.getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay().getRealMetrics(m);return m;}
    static void execute(Context context, JSONObject request, final Reply reply) {
        try {
            String action=request.getString("action");
            if(action.equals("status")) { reply.done(status(context));return; }
            if(action.equals("lock")) {
                if(!admin(context))throw new IllegalStateException("Ative o administrador Nexus para bloquear a tela");
                ((DevicePolicyManager)context.getSystemService(Context.DEVICE_POLICY_SERVICE)).lockNow();
                reply.done(result(true,"accepted",true));return;
            }
            final ControlAccessibility service=instance;
            if(service==null)throw new IllegalStateException("Ative a Acessibilidade do Nexus nas configurações Android");
            int global=-1;
            if(action.equals("home"))global=GLOBAL_ACTION_HOME;
            if(action.equals("back"))global=GLOBAL_ACTION_BACK;
            if(action.equals("recents"))global=GLOBAL_ACTION_RECENTS;
            if(action.equals("notifications"))global=GLOBAL_ACTION_NOTIFICATIONS;
            if(action.equals("quick_settings"))global=GLOBAL_ACTION_QUICK_SETTINGS;
            if(global!=-1) { boolean accepted=service.performGlobalAction(global);reply.done(result(accepted,"accepted",accepted));return; }
            if(!action.equals("tap")&&!action.equals("swipe"))throw new IllegalArgumentException("Ação não suportada");
            android.util.DisplayMetrics display=metrics(context);
            float x=(float)request.getDouble("x"), y=(float)request.getDouble("y");
            float x2=action.equals("swipe")?(float)request.getDouble("x2"):x;
            float y2=action.equals("swipe")?(float)request.getDouble("y2"):y;
            if(!Float.isFinite(x)||!Float.isFinite(y)||!Float.isFinite(x2)||!Float.isFinite(y2)||x<0||y<0||x2<0||y2<0||x>=display.widthPixels||x2>=display.widthPixels||y>=display.heightPixels||y2>=display.heightPixels)throw new IllegalArgumentException("Coordenadas fora da tela");
            long duration=action.equals("tap")?80:request.optLong("duration_ms",400);
            if(duration<50||duration>2000)throw new IllegalArgumentException("Duração deve ser 50 a 2000 ms");
            Path path=new Path();path.moveTo(x,y);if(action.equals("swipe"))path.lineTo(x2,y2);
            GestureDescription gesture=new GestureDescription.Builder().addStroke(new GestureDescription.StrokeDescription(path,0,duration)).build();
            boolean accepted=service.dispatchGesture(gesture,new GestureResultCallback(){
                @Override public void onCompleted(GestureDescription g){reply.done(result(true,"completed",true));}
                @Override public void onCancelled(GestureDescription g){reply.done(result(false,"error","Gesto cancelado pelo Android"));}
            },null);
            if(!accepted)reply.done(result(false,"error","Gesto recusado pelo Android"));
        } catch(Exception error) { reply.done(result(false,"error",error.getMessage()==null?"Falha Android":error.getMessage())); }
    }
}
