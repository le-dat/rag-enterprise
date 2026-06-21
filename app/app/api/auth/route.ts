import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(request: Request) {
  try {
    const { role, department, user_id } = await request.json();
    const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || "http://localhost:8000";

    const response = await fetch(`${fastapiUrl}/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ role, department, user_id }),
    });

    if (!response.ok) {
      const errorMsg = await response.text();
      return NextResponse.json(
        { error: `Backend authentication failed: ${errorMsg}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    const token = data.token;
    const resolvedUserId = data.user_id;

    // Set the cookie securely
    const cookieStore = await cookies();
    cookieStore.set("session_token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24, // 24 hours
      path: "/",
    });

    // Also store user info in non-httpOnly cookie for frontend display
    cookieStore.set("user_info", JSON.stringify({
      user_id: resolvedUserId,
      role,
      department
    }), {
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24,
      path: "/",
    });

    return NextResponse.json({ success: true, user_id: resolvedUserId });
  } catch (error: any) {
    console.error("Auth proxy error:", error);
    return NextResponse.json(
      { error: `Internal server error: ${error.message}` },
      { status: 500 }
    );
  }
}

export async function DELETE() {
  // Logout route: delete cookies
  const cookieStore = await cookies();
  cookieStore.delete("session_token");
  cookieStore.delete("user_info");
  return NextResponse.json({ success: true });
}
