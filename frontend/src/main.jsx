import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { I18n } from 'aws-amplify/utils';
import { translations } from '@aws-amplify/ui-react';
import { Amplify } from 'aws-amplify';

I18n.putVocabularies(translations);
I18n.setLanguage('pt')

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_QamhgZpjk',
      userPoolClientId: '42i5j6t6mse4k39899prf23gvk',
    }
  }
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)