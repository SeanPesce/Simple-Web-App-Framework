# Simple Web App Framework  

**Author: Sean Pesce**  

## Overview  

Python 3 framework I developed for quickly prototyping web apps (e.g., server emulators). This code is not considered safe for use on public hosts.  

## Usage  

Start the web app from the command line like so:

```
python3 ./web_server.py <port> [PEM certificate file] [private key file]
```

The server automatically listens on all interfaces (0.0.0.0). If file paths are provided for a certificate and private key, the server will automatically use TLS (HTTPS). If not, the server will automatically serve plaintext HTTP.

For implementing a web app, the vast majority of common use-cases are demonstrated by the example implementations in [endpoints.py](https://github.com/SeanPesce/Simple-Web-App-Framework/blob/main/endpoints.py) (generally speaking, most new code should be added to this file).  

## Disclaimer  

This code was not developed with security in mind, and likely contains vulnerabilities. For that reason, live implementations should never be exposed on a network for an extended period of time (if at all).

## License  

None yet.  

---------------------------------------------

For inquiries and/or information about me, visit my **[personal website](https://SeanPesce.github.io)**.  
