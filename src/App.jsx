import React, { useState } from 'react';
import { 
  Container, 
  Typography, 
  TextField, 
  Button, 
  Box, 
  Paper,
  CssBaseline,
  AppBar,
  Toolbar
} from '@mui/material';
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

function App() {
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Here you would typically fetch the content using the URL
    // For now, we'll just set some placeholder content
    setContent(`Content fetched from ${url}`);
  };

  return (
    <>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6">Mini Bookmark</Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="md">
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Mini Bookmark
          </Typography>
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Enter URL"
              variant="outlined"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              sx={{ mb: 2 }}
            />
            <Button 
              type="submit" 
              variant="contained" 
              color="primary"
              fullWidth
            >
              Fetch Content
            </Button>
          </form>
          <Paper elevation={3} sx={{ p: 2, mt: 2, minHeight: 200 }}>
            <Typography variant="body1">
              {content || 'Fetched content will appear here'}
            </Typography>
          </Paper>
        </Box>
      </Container>
      <Box component="footer" sx={{ bgcolor: 'background.paper', py: 6 }}>
        <Container maxWidth="lg">
          <Typography variant="body2" color="text.secondary" align="center">
            © 2023 Mini Bookmark. All rights reserved.
          </Typography>
        </Container>
      </Box>
    </>
  );
}

export default App;