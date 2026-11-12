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