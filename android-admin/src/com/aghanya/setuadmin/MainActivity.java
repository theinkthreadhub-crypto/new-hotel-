package com.aghanya.setuadmin;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

// Setu Hotel Super Admin: Setu Cloud ka /admin.html WebView mein (Library ERP ke SetuAdmin jaisa). Backup save/share ke liye SA bridge.
public class MainActivity extends Activity {
    static final String HOST = "setu-cloud.theinkthreadhub.workers.dev";
    static final String START = "https://" + HOST + "/admin.html";
    WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#eef1f6"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // Admin Key yaad rakhne ke liye ("Remember on this device")
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setSupportMultipleWindows(false);
        s.setUserAgentString(s.getUserAgentString() + " SetuHotelAdminApp/1.0");
        web.addJavascriptInterface(new Bridge(), "SA");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                return openOutside(r.getUrl());
            }
            @SuppressWarnings("deprecation")
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, String url) {
                return openOutside(Uri.parse(url));
            }
            @Override
            public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {
                if (r.isForMainFrame()) showOffline();
            }
            @SuppressWarnings("deprecation")
            @Override
            public void onReceivedError(WebView v, int code, String desc, String url) {
                if (url != null && url.equals(v.getUrl())) showOffline();
            }
        });
        setContentView(web);
        if (state != null) web.restoreState(state);
        else web.loadUrl(START);
    }

    // Apni site app ke andar; WhatsApp, phone call, baaki links bahar wale app mein
    boolean openOutside(Uri u) {
        String scheme = u.getScheme() == null ? "" : u.getScheme();
        if ((scheme.equals("https") || scheme.equals("http")) && HOST.equals(u.getHost())) return false;
        try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { }
        return true;
    }

    void showOffline() {
        String html = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'></head>"
            + "<body style='font-family:sans-serif;background:#f4f6fa;color:#1d2433;text-align:center;padding:60px 24px'>"
            + "<h2 style='color:#0f172a'>No internet</h2><p>Connect to the internet and try again.</p>"
            + "<button onclick=\"location.href='" + START + "'\" style='background:#2b4c7e;color:#fff;border:0;border-radius:8px;padding:12px 28px;font-size:16px'>Try again</button>"
            + "<p style='margin-top:40px;color:#6b7385;font-size:13px'>Setu Hotel Admin &middot; Aghanya Devanya Enterprises</p></body></html>";
        web.loadDataWithBaseURL(START, html, "text/html", "utf-8", START);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    protected void onResume() { super.onResume(); web.onResume(); }

    @Override
    protected void onPause() { web.onPause(); super.onPause(); }

    // Sirf ek kaam: backup / file ko save ya share karna (Gmail, WhatsApp, Drive)
    class Bridge {
        @JavascriptInterface
        public void save(final String name, final String mime, final String b64) {
            runOnUiThread(new Runnable() { @Override public void run() {
                try {
                    File dir = new File(getCacheDir(), "share"); dir.mkdirs();
                    String safe = name == null ? "file" : name.replaceAll("[^A-Za-z0-9_.-]", "_");
                    try (OutputStream o = new FileOutputStream(new File(dir, safe))) { o.write(Base64.decode(b64, Base64.DEFAULT)); }
                    Uri u = Uri.parse("content://com.aghanya.setuadmin.share/" + safe);
                    Intent i = new Intent(Intent.ACTION_SEND);
                    i.setType(mime == null || mime.isEmpty() ? "application/octet-stream" : mime);
                    i.putExtra(Intent.EXTRA_STREAM, u);
                    i.setClipData(ClipData.newRawUri(safe, u));
                    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(i, "Save or send " + safe));
                } catch (Exception e) { Toast.makeText(MainActivity.this, "Could not save: " + e.getMessage(), Toast.LENGTH_LONG).show(); }
            } });
        }
    }
}
