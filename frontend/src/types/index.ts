export interface Business {
  id: string;
  owner_name: string;
  email: string;
  business_name: string;
  phone: string | null;
  currency: string;
  created_at: string;
}

export type InvoiceStatus = "DRAFT" | "SENT" | "PAID" | "CANCELLED";

export interface Invoice {
  id: string;
  number: string;
  customer_id: string;
  customer_name: string;
  description: string;
  amount: string;
  currency: string;
  due_date: string;
  status: InvoiceStatus;
  display_status: InvoiceStatus | "OVERDUE";
  public_token: string;
  created_at: string;
}

export interface CustomerSummary {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  created_at: string;
  invoice_count: number;
  total_paid: string;
  outstanding: string;
}

export interface DashboardSummary {
  total_revenue: string;
  pending_amount: string;
  pending_count: number;
  overdue_amount: string;
  overdue_count: number;
  paid_count: number;
  recent_payments: {
    id: string;
    invoice_number: string;
    customer_name: string;
    amount: string;
    currency: string;
    verified_at: string;
  }[];
}

export interface InvoiceDraft {
  customer_name: string | null;
  customer_email: string | null;
  description: string | null;
  amount: string | null;
  due_date: string | null;
}

export interface AIParseResult {
  status: "ready" | "needs_clarification";
  draft: InvoiceDraft;
  missing_fields: string[];
  question: string | null;
  existing_customer: boolean;
  similar_customers: { id: string; name: string }[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface PendingActionOut {
  id: string;
  action_type: string;
  summary: string;
  expires_at: string;
}

export interface ReminderCandidate {
  invoice_id: string;
  number: string;
  customer_name: string;
  amount: string;
  currency: string;
  due_date: string;
  display_status: string;
  days_overdue: number;
  has_draft: boolean;
  last_reminded_at: string | null;
}

export interface Reminder {
  id: string;
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  amount: string;
  currency: string;
  due_date: string;
  invoice_status: string;
  message: string;
  status: "DRAFT" | "APPROVED" | "DISMISSED";
  created_at: string;
  approved_at: string | null;
}

export interface InsightsResponse {
  stats: {
    monthly_revenue: { label: string; revenue_usd: string; payments: number }[];
    overdue_aging: { bucket: string; count: number; amount_usd: string }[];
  };
  insights: string[];
  ai_generated: boolean;
}