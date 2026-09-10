"use strict";

const storageKey = "neuraConnectConversationId";
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatHistory = document.getElementById("chat-history");
const sendButton = document.getElementById("send-button");
const resetButton = document.getElementById("reset-button");
const loadingStatus = document.getElementById("loading-status");
const errorStatus = document.getElementById("error-status");
let conversationId = sessionStorage.getItem(storageKey);
let isLoading = false;

function setLoading(loading, message = "Finding the best answer…") {
  isLoading = loading;
  sendButton.disabled = loading;
  resetButton.disabled = loading;
  messageInput.disabled = loading;
  loadingStatus.hidden = !loading;
  loadingStatus.textContent = message;
}
function showError(message) { errorStatus.textContent = message; errorStatus.hidden = false; }
function clearError() { errorStatus.textContent = ""; errorStatus.hidden = true; }
function addMessage(role, text, metadata = []) {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Support assistant";
  const content = document.createElement("p");
  content.textContent = text;
  article.append(label, content);
  if (metadata.length) {
    const details = document.createElement("p");
    details.className = "message-metadata";
    details.textContent = metadata.join(" · ");
    article.append(details);
  }
  chatHistory.append(article);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}
function welcomeMessage() { chatHistory.replaceChildren(); addMessage("assistant", "Hello! How can I help you today?"); }
function responseMetadata(data) {
  const details = [];
  if (data.intent) details.push(`Intent: ${data.intent.replaceAll("_", " ")}`);
  if (data.sentiment) details.push(`Sentiment: ${data.sentiment.toLowerCase()}`);
  if (data.context_used) details.push("Context used");
  if (data.is_fallback) details.push("General support guidance");
  return details;
}
async function parseResponse(response) {
  try { return await response.json(); } catch { throw new Error("The server returned an unexpected response."); }
}
async function sendMessage(event) {
  event.preventDefault();
  if (isLoading) return;
  const message = messageInput.value.trim();
  if (!message) { showError("Please enter a support question."); messageInput.focus(); return; }
  clearError(); addMessage("user", message); messageInput.value = ""; setLoading(true);
  try {
    const payload = { message };
    if (conversationId) payload.conversation_id = conversationId;
    const response = await fetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await parseResponse(response);
    if (!response.ok) throw new Error(data.error || "Unable to send your message.");
    conversationId = String(data.conversation_id);
    sessionStorage.setItem(storageKey, conversationId);
    addMessage("assistant", data.response, responseMetadata(data));
  } catch (error) { showError(error instanceof Error ? error.message : "Unable to reach support right now."); }
  finally { setLoading(false); messageInput.focus(); }
}
async function resetConversation() {
  if (isLoading) return;
  clearError(); setLoading(true, "Starting a new conversation…");
  try {
    const payload = conversationId ? { conversation_id: conversationId } : {};
    const response = await fetch("/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await parseResponse(response);
    if (!response.ok) throw new Error(data.error || "Unable to reset the conversation.");
    conversationId = String(data.conversation_id);
    sessionStorage.setItem(storageKey, conversationId);
    welcomeMessage();
  } catch (error) { showError(error instanceof Error ? error.message : "Unable to reset the conversation."); }
  finally { setLoading(false); messageInput.focus(); }
}
chatForm.addEventListener("submit", sendMessage);
messageInput.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); chatForm.requestSubmit(); } });
resetButton.addEventListener("click", resetConversation);
