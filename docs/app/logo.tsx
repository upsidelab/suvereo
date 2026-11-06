import styles from "./logo.module.css";
import Image from "next/image";
import Link from "next/link";

export default function Logo() {
  return (
    <Link href="/" className="x:flex x:items-center">
      <Image src={`${process.env.NEXT_PUBLIC_BASE_PATH}/logo.png`} alt="Suvereo" height={32} width={32} className={styles.logo__image} />
      <b>suvereo.</b>
    </Link>
  );
}
