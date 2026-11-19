package org.nexusmind.control;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;

public final class BridgeService extends Service {
    static final int PORT=18764;
    static volatile long until=0;
    static volatile String session="";
    java.util.LinkedHashMap<String,Boolean> nonces=new java.util.LinkedHashMap<>();
    volatile boolean running;
    ServerSocket server;
    Handler main=new Handler(Looper.getMainLooper());
    @Override public IBinder onBind(Intent intent){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&"STOP".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
        if(running)return START_NOT_STICKY;
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel("nexus-local","Nexus controle local",NotificationManager.IMPORTANCE_LOW));
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,BridgeService.class).setAction("STOP"),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent open=PendingIntent.getActivity(this,2,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Notification note=new Notification.Builder(this,"nexus-local").setSmallIcon(android.R.drawable.ic_lock_idle_lock).setContentTitle("Nexus: controle local ativo").setContentText("Sessão de até 15 minutos. Toque para revisar.").setContentIntent(open).setOngoing(true).addAction(android.R.drawable.ic_menu_close_clear_cancel,"Parar",stop).build();
        startForeground(1,note);session=MainActivity.randomHex(16);until=SystemClock.elapsedRealtime()+15*60*1000;running=true;
        new Thread(()->serve(),"nexus-loopback").start();return START_NOT_STICKY;
    }
    void serve(){
        try(ServerSocket listener=new ServerSocket(PORT,4,InetAddress.getByName("127.0.0.1"))){
            server=listener;listener.setSoTimeout(1000);
            while(running&&SystemClock.elapsedRealtime()<until){
                try(Socket socket=listener.accept()){socket.setSoTimeout(2000);handle(socket);}
                catch(SocketTimeoutException ignored){}
                catch(Exception ignored){ /* No request contents or tokens are logged. */ }
            }
        }catch(Exception ignored){}finally{running=false;until=0;stopSelf();}
    }
    String line(InputStream input,long deadline)throws Exception{
        java.io.ByteArrayOutputStream bytes=new java.io.ByteArrayOutputStream();int c;
        while((c=input.read())!=-1){if(SystemClock.elapsedRealtime()>deadline)throw new IllegalArgumentException("read timeout");if(c=='\n')break;if(c!='\r')bytes.write(c);if(bytes.size()>2048)throw new IllegalArgumentException("header too long");}
        return bytes.toString("US-ASCII");
    }
    void send(Socket socket,int status,JSONObject value,String nonce)throws Exception{
        byte[] bytes=value.toString().getBytes(StandardCharsets.UTF_8);
        String signature=Auth.sign(MainActivity.token(this),"response\n"+nonce+"\n"+new String(bytes,StandardCharsets.UTF_8));
        String header="HTTP/1.1 "+status+" Result\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nConnection: close\r\nX-Nexus-Signature: "+signature+"\r\nContent-Length: "+bytes.length+"\r\n\r\n";
        socket.getOutputStream().write(header.getBytes(StandardCharsets.US_ASCII));socket.getOutputStream().write(bytes);socket.getOutputStream().flush();
    }
    void handle(Socket socket)throws Exception{
        long deadline=SystemClock.elapsedRealtime()+3500;
        InputStream input=socket.getInputStream();String request=line(input,deadline),nonce="",signature="",timestamp="",sessionId="";int length=-1;int total=request.length();
        while(true){String header=line(input,deadline);total+=header.length();if(total>8192)throw new IllegalArgumentException("headers too long");if(header.isEmpty())break;
            int colon=header.indexOf(':');if(colon<1)continue;String key=header.substring(0,colon).trim();String value=header.substring(colon+1).trim();
            if(key.equalsIgnoreCase("X-Nexus-Nonce"))nonce=value;
            if(key.equalsIgnoreCase("X-Nexus-Time"))timestamp=value;
            if(key.equalsIgnoreCase("X-Nexus-Session"))sessionId=value;
            if(key.equalsIgnoreCase("X-Nexus-Signature"))signature=value;
            if(key.equalsIgnoreCase("Content-Length"))length=Integer.parseInt(value);
            if(key.equalsIgnoreCase("Transfer-Encoding")){send(socket,400,ControlAccessibility.result(false,"error","Transfer encoding unsupported"),nonce);return;}
        }
        if(!running||SystemClock.elapsedRealtime()>=until){send(socket,403,ControlAccessibility.result(false,"error","Sessão expirada"),nonce);return;}
        if(!request.equals("POST /v1/action HTTP/1.1")||length<2||length>4096){send(socket,400,ControlAccessibility.result(false,"error","Pedido não suportado"),nonce);return;}
        byte[] body=new byte[length];int offset=0;while(offset<length){int count=input.read(body,offset,length-offset);if(count<0||SystemClock.elapsedRealtime()>deadline)throw new IllegalArgumentException("short or slow body");offset+=count;}
        String raw=new String(body,StandardCharsets.UTF_8);
        if(!nonce.matches("[a-f0-9]{32}")||!timestamp.matches("[0-9]{13}")||!signature.matches("[a-f0-9]{64}")||!session.equals(sessionId)||Math.abs(System.currentTimeMillis()-Long.parseLong(timestamp))>30000||nonces.containsKey(nonce)||!Auth.equal(signature,Auth.sign(MainActivity.token(this),"request\n"+sessionId+"\n"+nonce+"\n"+timestamp+"\n"+raw))){send(socket,401,ControlAccessibility.result(false,"error","Pareamento inválido ou expirado"),nonce);return;}
        if(nonces.size()>=256){send(socket,429,ControlAccessibility.result(false,"error","Limite de 256 comandos nesta sessão; inicie outra sessão"),nonce);return;}
        nonces.put(nonce,true);
        JSONObject command=new JSONObject(new String(body,StandardCharsets.UTF_8));
        CountDownLatch ready=new CountDownLatch(1);AtomicReference<JSONObject> response=new AtomicReference<>();
        final long actionDeadline=SystemClock.elapsedRealtime()+1000;
        main.post(()->{if(!running||SystemClock.elapsedRealtime()>=until||SystemClock.elapsedRealtime()>actionDeadline){response.set(ControlAccessibility.result(false,"error","Pedido expirado sem execução"));ready.countDown();return;}ControlAccessibility.execute(this,command,value->{if(response.compareAndSet(null,value))ready.countDown();});});
        if(!ready.await(4,TimeUnit.SECONDS)){send(socket,504,ControlAccessibility.result(false,"error","Android não confirmou a ação"),nonce);return;}
        send(socket,200,response.get(),nonce);
    }
    @Override public void onDestroy(){running=false;until=0;try{if(server!=null)server.close();}catch(Exception ignored){}stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy();}
}
