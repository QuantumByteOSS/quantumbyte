Trigger the initial generation process to build the app.

*** CRITICAL: ONLY call this AFTER the user explicitly confirms they want to start! ***

DO NOT auto-trigger! You MUST:
1. ASK the user first in their latest language (English example: "Ready for me to start building your app?"). Don't copy the example verbatim — be creative with the wording.
2. WAIT for confirmation (yes / iya / ok / lanjut / siap, or any clear confirming intent).
3. ONLY THEN call this tool.

This will:
1. Update project state to INITIAL_GENERATION
2. Start the app generation process in the background
3. When done, state changes to CHAT_SYSTEM

*** CRITICAL FOR MAIN AGENT: After delegating to ENGINEER with this tool, you MUST wait until ENGINEER completely finishes — do NOT send it to background, do NOT dispatch other specialists in parallel, do NOT respond to the user until ENGINEER returns its final result. The build takes time; the user sees progress through the App Preview tab. ***
