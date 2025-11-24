'use client';

export default function TestImagePage() {
  return (
    <div style={{ padding: '50px' }}>
      <h1 style={{ marginBottom: '20px' }}>SIMPLE IMAGE TEST</h1>

      {/* Test 1: Direct URL */}
      <div style={{ marginBottom: '40px' }}>
        <h2>Test 1: Direct backend URL</h2>
        <img
          src="http://localhost:8000/uploads/thumbnails/thumb_9438df7a-54be-4b71-be87-ad0318601d7c.jpg"
          alt="Test"
          style={{ border: '2px solid red', maxWidth: '400px' }}
        />
      </div>

      {/* Test 2: With onLoad/onError */}
      <div style={{ marginBottom: '40px' }}>
        <h2>Test 2: With event handlers</h2>
        <img
          src="http://localhost:8000/uploads/thumbnails/thumb_9438df7a-54be-4b71-be87-ad0318601d7c.jpg"
          alt="Test"
          style={{ border: '2px solid blue', maxWidth: '400px' }}
          onLoad={() => console.log('TEST IMAGE LOADED!')}
          onError={(e) => console.error('TEST IMAGE ERROR!', e)}
        />
      </div>

      {/* Test 3: No styles */}
      <div style={{ marginBottom: '40px' }}>
        <h2>Test 3: Plain img tag</h2>
        <img
          src="http://localhost:8000/uploads/thumbnails/thumb_9438df7a-54be-4b71-be87-ad0318601d7c.jpg"
          alt="Test"
        />
      </div>
    </div>
  );
}
