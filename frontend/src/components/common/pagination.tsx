import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatNumber } from "@/utils/format";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

/** List pagination footer with result count. */
export function Pagination({ page, pages, total, onPageChange }: PaginationProps) {
  if (total === 0) return null;
  return (
    <div className="flex flex-col items-center justify-between gap-3 pt-4 sm:flex-row">
      <p className="text-sm text-muted-foreground">
        Page {page} of {Math.max(pages, 1)} · {formatNumber(total)} results
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
