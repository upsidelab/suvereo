import React from 'react';
import {
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from "@/components/ui/pagination";

interface RenderPaginationItemsProps {
  currentPage: number;
  totalPages: number;
  handlePageChange: (page: number, event?: React.MouseEvent) => void;
}

const RenderPaginationItems: React.FC<RenderPaginationItemsProps> = ({ currentPage, totalPages, handlePageChange }) => {
  const pages = [];
  const startPage = Math.max(1, currentPage - 1);
  const endPage = Math.min(totalPages, currentPage + 1);

  if (startPage > 1) {
    pages.push(
      <PaginationItem key={1}>
        <PaginationLink href="#" onClick={(e) => handlePageChange(1, e)}>
          1
        </PaginationLink>
      </PaginationItem>
    );
    if (startPage > 2) {
      pages.push(
        <PaginationItem key="start-ellipsis">
          <PaginationEllipsis onPageSelect={handlePageChange} totalPages={totalPages} isLeft={true} currentPage={currentPage} />
        </PaginationItem>
      );
    }
  }

  for (let page = startPage; page <= endPage; page++) {
    pages.push(
      <PaginationItem key={page}>
        <PaginationLink
          href="#"
          isActive={page === currentPage}
          onClick={(e) => handlePageChange(page, e)}
        >
          {page}
        </PaginationLink>
      </PaginationItem>
    );
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      pages.push(
        <PaginationItem key="end-ellipsis">
          <PaginationEllipsis onPageSelect={handlePageChange} totalPages={totalPages} isLeft={false} currentPage={currentPage} />
        </PaginationItem>
      );
    }
    pages.push(
      <PaginationItem key={totalPages}>
        <PaginationLink href="#" onClick={(e) => handlePageChange(totalPages, e)}>
          {totalPages}
        </PaginationLink>
      </PaginationItem>
    );
  }

  return <>{pages}</>;
};

export default RenderPaginationItems;