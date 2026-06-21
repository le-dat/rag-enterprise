import { NextRequest, NextResponse } from "next/server";

async function handleProxy(
  request: NextRequest,
  { params }: { params: Promise<{ proxy: string[] }> }
) {
  const { proxy } = await params;
  const token = request.cookies.get("session_token")?.value;
  
  // Construct destination URL
  const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || "http://localhost:8000";
  const searchParams = request.nextUrl.searchParams.toString();
  const destPath = proxy.join("/");
  const destUrl = `${fastapiUrl}/${destPath}${searchParams ? `?${searchParams}` : ""}`;

  console.log(`[Proxy] Routing ${request.method} /api/${destPath} -> ${destUrl}`);

  const headers: Record<string, string> = {};
  
  // Forward content-type if present
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    // Read request body for POST/PUT/PATCH/DELETE
    let body: any = null;
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method)) {
      body = await request.text();
    }

    const response = await fetch(destUrl, {
      method: request.method,
      headers,
      body: body || undefined,
    });

    // Check if it's an SSE stream
    const resContentType = response.headers.get("content-type") || "";
    if (resContentType.includes("text/event-stream")) {
      return new NextResponse(response.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache, no-transform",
          "Connection": "keep-alive",
        },
      });
    }

    // Standard response
    const data = await response.text();
    return new NextResponse(data, {
      status: response.status,
      headers: {
        "Content-Type": resContentType,
      },
    });
  } catch (error: any) {
    console.error(`[Proxy] Error routing to ${destUrl}:`, error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET(request: NextRequest, context: any) {
  return handleProxy(request, context);
}

export async function POST(request: NextRequest, context: any) {
  return handleProxy(request, context);
}

export async function PUT(request: NextRequest, context: any) {
  return handleProxy(request, context);
}

export async function DELETE(request: NextRequest, context: any) {
  return handleProxy(request, context);
}
