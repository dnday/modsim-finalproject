/*
 * Universal Android SSL Pinning Bypass
 * Useful as a fallback if HTTP Toolkit's automatic unpinning fails.
 * Usage: frida -U -f com.icon.pln123 -l frida_ssl_bypass.js --no-pause
 */
Java.perform(function() {
    console.log("[*] Starting Universal SSL Pinning Bypass...");

    // 1. TrustManagerImpl (Android > 7)
    try {
        var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TrustManagerImpl.verifyChain.implementation = function(untrustedChain, trustAnchorChain, host, clientAuth, ocspData, tlsSctData) {
            console.log("[+] Bypassing TrustManagerImpl.verifyChain()");
            return untrustedChain;
        };
    } catch (err) {
        console.log("[-] TrustManagerImpl not found");
    }

    // 2. OkHttp3 CertificatePinner
    try {
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            console.log("[+] Bypassing OkHttp3 CertificatePinner check()");
            return;
        };
    } catch (err) {
        console.log("[-] OkHttp3 CertificatePinner not found");
    }

    // 3. NetworkSecurityConfig (Android > 7)
    try {
        var NetworkSecurityConfig = Java.use('android.security.net.config.NetworkSecurityConfig');
        NetworkSecurityConfig.getDefaultBuilder.implementation = function(context) {
            console.log("[+] Bypassing NetworkSecurityConfig");
            return this.getDefaultBuilder(context);
        };
    } catch (err) {
        // Ignore
    }

    console.log("[*] Bypass installed successfully.");
});
