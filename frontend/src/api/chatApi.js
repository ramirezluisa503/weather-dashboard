import { request } from './client';

export const listConversations = () => request('/chat/conversations/');

export const createConversation = () => request('/chat/conversations/', { method: 'POST' });

export const getConversation = (id) => request(`/chat/conversations/${id}/`);

export const askQuestion = (id, content) =>
  request(`/chat/conversations/${id}/messages/`, { method: 'POST', body: { content } });
