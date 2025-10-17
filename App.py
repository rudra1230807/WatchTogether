# App.py
import streamlit as st
from streamlit.components.v1 import html

# must be the first Streamlit command
st.set_page_config(page_title="🎬 Watch Together", layout="centered")
st.title("🎥 Watch Together - Realtime YouTube Party (no reruns)")

# Get room & user from Streamlit only to pass into iframe
room_id = st.text_input("Room Name (shared):")
user_name = st.text_input("Your Name:")

# NOTE: If your FastAPI WS server is not on the same host, replace this
# with the public host:port or wss://... when deployed.
# For local testing keep ws://127.0.0.1:8000
WS_HOST = "ws://127.0.0.1:8000"  # <-- change to wss://your-domain if deployed

if room_id and user_name:
    # The entire interactive UI (video URL input, play/pause/seek, chat) lives inside this single iframe.
    # This avoids any streamlit rerun and keeps one stable WebSocket connection.
    html_code = f"""
    <div style="font-family: Arial, sans-serif; max-width:760px;">
      <div style="display:flex; gap:10px; align-items:center;">
        <div><b>Room:</b> {room_id}</div>
        <div><b>User:</b> {user_name}</div>
      </div>

      <div style="margin-top:10px;">
        <input id="video_input" type="text" placeholder="Paste YouTube URL and click Update" style="width:70%;">
        <button id="update_video_btn">Update Video</button>
      </div>

      <div id="player" style="margin-top:10px;"></div>

      <div style="margin-top:8px;">
        <button id="play_btn">Play</button>
        <button id="pause_btn">Pause</button>
        <label style="margin-left:10px;">Seek (seconds):</label>
        <input id="seek_input" type="number" min="0" value="0" style="width:80px;">
        <button id="seek_btn">Go</button>
      </div>

      <div style="margin-top:10px; display:flex;">
        <div id="chat" style="flex:1; height:180px; overflow-y:auto; border:1px solid #ddd; padding:6px; background:#fafafa;"></div>
        <div style="width:220px; margin-left:10px;">
          <input id="chat_input" type="text" placeholder="Type message..." style="width:100%;"><br>
          <button id="send_btn" style="margin-top:6px; width:100%;">Send</button>
        </div>
      </div>
    </div>

    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
    (function() {{
      const WS_URL = "{WS_HOST}/ws/{room_id}";
      const userName = "{user_name}";

      // open websocket
      const ws = new WebSocket(WS_URL);

      let player = null;
      let currentVideoUrl = "";
      let pendingInitialState = null;

      // expose callback for YouTube API
      window.onYouTubeIframeAPIReady = function() {{
        // if server sent initial state already, use it; else player will be created when we get a video
        if (pendingInitialState) {{
          createOrUpdatePlayer(pendingInitialState.video_url, pendingInitialState.time);
          pendingInitialState = null;
        }} else {{
          // create a placeholder player with a default id — will be replaced when server sends video
          createOrUpdatePlayer("", 0);
        }}
      }};

      function createOrUpdatePlayer(video_url, startSeconds) {{
        const vid = extractVideoId(video_url);
        const videoIdToLoad = vid || "dQw4w9WgXcQ"; // fallback
        if (player && player.loadVideoById) {{
          // update existing player
          player.loadVideoById({{videoId: videoIdToLoad, startSeconds: Math.floor(startSeconds)}});
        }} else {{
          // create new player
          player = new YT.Player('player', {{
            height: '390',
            width: '640',
            videoId: videoIdToLoad,
            playerVars: {{autoplay: 0, controls: 1, start: Math.floor(startSeconds)}}
          }});
        }}
        currentVideoUrl = video_url || "";
      }}

      function extractVideoId(url) {{
        if (!url) return null;
        // handle both v= and youtu.be short links
        try {{
          const vMatch = url.match(/[?&]v=([A-Za-z0-9_-]{{11}})/);
          if (vMatch) return vMatch[1];
          const bMatch = url.match(/youtu\\.be\\/([A-Za-z0-9_-]{{11}})/);
          if (bMatch) return bMatch[1];
        }} catch(e){{}}
        return null;
      }}

      // When WS opens, server will send current room state (video_url, state, time, chat)
      ws.onopen = function() {{
        console.log("ws open", WS_URL);
      }};

      ws.onclose = function(e) {{
        console.warn("ws closed", e);
        // show message in chat area
        appendSystemMessage("Disconnected from server.");
      }};

      ws.onerror = function(err) {{
        console.error("ws error", err);
        appendSystemMessage("WebSocket error.");
      }};

      ws.onmessage = function(event) {{
        try {{
          const data = JSON.parse(event.data);
          // If there's a video_url and it's different, load it and start at data.time
          if (data.video_url && data.video_url !== currentVideoUrl) {{
            if (typeof YT === "undefined" || typeof YT.Player === "undefined") {{
              // YouTube API not ready yet; store initial state to apply in onYouTubeIframeAPIReady
              pendingInitialState = data;
            }} else {{
              createOrUpdatePlayer(data.video_url, data.time || 0);
            }}
            currentVideoUrl = data.video_url || "";
          }} else {{
            // same video: apply play/pause/seek
            if (player) {{
              const targetTime = data.time || 0;
              if (data.state === "play") {{
                // play only if not already playing or if time differs significantly
                try {{
                  const s = player.getCurrentTime ? player.getCurrentTime() : null;
                  if (s !== null && Math.abs(s - targetTime) > 1) {{
                    player.seekTo(targetTime, true);
                  }}
                  if (player.getPlayerState() !== 1) player.playVideo();
                }} catch(e) {{
                  // ignore if player not ready
                  player.seekTo(targetTime, true);
                  player.playVideo();
                }}
              }} else if (data.state === "pause") {{
                try {{
                  if (player.getPlayerState() !== 2) player.pauseVideo();
                  player.seekTo(targetTime, true);
                }} catch(e) {{
                  player.seekTo(targetTime, true);
                }}
              }}
            }}
          }}

          // Chat update
          if (Array.isArray(data.chat)) {{
            const chatDiv = document.getElementById('chat');
            chatDiv.innerHTML = "";
            for (const m of data.chat) {{
              const el = document.createElement('div');
              el.innerHTML = "<b>" + escapeHtml(m.user) + ":</b> " + escapeHtml(m.msg);
              chatDiv.appendChild(el);
            }}
            chatDiv.scrollTop = chatDiv.scrollHeight;
          }}
        }} catch (err) {{
          console.error("error parsing ws message", err);
        }}
      }};

      // Helpers
      function appendSystemMessage(txt) {{
        const chatDiv = document.getElementById('chat');
        const el = document.createElement('div');
        el.style.color = '#666';
        el.innerHTML = "<i>" + escapeHtml(txt) + "</i>";
        chatDiv.appendChild(el);
        chatDiv.scrollTop = chatDiv.scrollHeight;
      }}
      function escapeHtml(s) {{
        if (!s) return "";
        return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      }}

      // wire up UI controls inside iframe:
      document.getElementById('update_video_btn').onclick = function() {{
        const url = document.getElementById('video_input').value.trim();
        if (!url) return;
        ws.send(JSON.stringify({{ action: "update_video", video_url: url }}));
        document.getElementById('video_input').value = "";
      }};

      document.getElementById('send_btn').onclick = function() {{
        const txt = document.getElementById('chat_input').value.trim();
        if (!txt) return;
        ws.send(JSON.stringify({{ action: "chat", user: userName, msg: txt }}));
        document.getElementById('chat_input').value = "";
      }};

      document.getElementById('play_btn').onclick = function() {{
        ws.send(JSON.stringify({{ action: "play" }}));
      }};

      document.getElementById('pause_btn').onclick = function() {{
        ws.send(JSON.stringify({{ action: "pause" }}));
      }};

      document.getElementById('seek_btn').onclick = function() {{
        const val = Number(document.getElementById('seek_input').value || 0);
        if (isNaN(val) || val < 0) return;
        ws.send(JSON.stringify({{ action: "seek", time: val }}));
      }};

    }})();
    </script>
    """

    html(html_code, height=760)
