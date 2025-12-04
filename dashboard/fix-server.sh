#!/bin/bash
# Fix Next.js Internal Server Error
# This script clears all caches and restores proper structure

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Fixing Next.js Dashboard Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop any running dev servers
echo "📛 Stopping any running dev servers..."
pkill -f "next dev" 2>/dev/null || true
sleep 2

# Clear all caches
echo "🗑️  Clearing caches..."
rm -rf .next
rm -rf node_modules/.cache
rm -rf .turbo

# Verify file structure
echo "📁 Verifying file structure..."
if [ ! -f "src/app/globals.css" ]; then
    echo "❌ Missing globals.css - creating..."
    cat > src/app/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF
fi

if [ ! -f "src/app/layout.tsx" ]; then
    echo "❌ Missing layout.tsx!"
    exit 1
fi

if [ ! -f "src/app/page.tsx" ]; then
    echo "❌ Missing page.tsx!"
    exit 1
fi

# Check for duplicate app directories
if [ -d "app" ] && [ -d "src/app" ]; then
    echo "⚠️  Found duplicate app directories - removing root app/..."
    rm -rf app
fi

echo "✅ File structure verified"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Start the dev server: npm run dev"
echo "   2. If errors persist, check:"
echo "      - Backend API is running on http://localhost:8000"
echo "      - Environment variables are set in .env.local"
echo "      - Browser console for client-side errors"
echo ""
echo "🌐 Start server: npm run dev"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

